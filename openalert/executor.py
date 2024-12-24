import copy
import json
import threading
from typing import Dict
from apscheduler.schedulers.background import BackgroundScheduler

import actions
from rule import RuleManager
from converter import Converter, QUERY, BOOL, MUST_NOT
from logger import openalert_logger
from opensearch_client import OpenSearchClient
from enhancements import EQLEnhancement, IndicatorMatchEnhancement
from ultils import ts_now, interval_to_seconds
from watcher import RulesWatcher, ExceptionsWatcher


METADATA = '_metadata'
INDEX = '_index'
ID = '_id'
RULE = 'rule'
RULE_NAME = 'name'
RULE_ID = 'id'
RULE_DESCRIPTION = 'description'
RISK_SCORE = 'risk_score'
SEVERITY_LABEL = 'severity_label'
RULE_TAGS = 'tags'
RULE_THREAT = 'threat'
EVENT = 'event'
TIMESTAMP = '@timestamp'
MATCH = 'match'
CREATED = 'created'

pattern_alert = {
    TIMESTAMP: '',
    METADATA: {INDEX: '', ID: ''},
    RULE: {RULE_NAME: '', RULE_ID: '', RULE_DESCRIPTION: '',
           RISK_SCORE: 0, SEVERITY_LABEL: '', RULE_TAGS: [], RULE_THREAT: []},
    EVENT:{MATCH: {}}
}


class Executor(RuleManager):
    def __init__(self, rules, disabled_rules, exceptions, config):
        super().__init__(rules, disabled_rules, exceptions)
        self.rules_folder = config['rule']['rulesFolder']
        self.exceptions_folder = config['rule']['exceptionsFolder']
        self.rules_watcher = RulesWatcher(self.rules_folder, self)
        self.exceptions_watcher = ExceptionsWatcher(self.exceptions_folder,self)
        self.converter = Converter()


        self.debug = config.get("debug", False)
        self.client = OpenSearchClient(config)
        self.writeBackIndex = config['opensearch']['writeBack']
        self.interval = config['rule']['schedule']['interval']
        self.bufferTime = config['rule']['schedule']['bufferTime']
        self.maxSignals = config['rule']['maxSignals']

        # jobs: { interval: job_id }
        self.jobs: Dict[int, str] = {}
        self.jobs_lock = threading.Lock()
        self.scheduler = BackgroundScheduler()

        openalert_logger.info('Pre-processing rules and exceptionsList...')
        self.preprocess()

        openalert_logger.info('Loading enhancer...')
        self.enhancers = {}
        self.load_enhancer()

        openalert_logger.info('Loading actions...')
        self.actions = {}
        self.load_actions()


    def preprocess(self):
        """Build OpenSearch query for Rule and ExceptionsList"""
        # Get DSL_Lucene query from Rule
        self.rules = self.converter.convert_all(self.rules, 'rules')

        # Get DSL_Lucene query from DisabledRule
        self.disabled_rules = self.converter.convert_all(self.disabled_rules, 'rules')

        # Get DSL_Lucene query from ExceptionsList
        self.exceptions = self.converter.convert_all(self.exceptions, 'exceptionsList')

        openalert_logger.info(r"Pre-processing completed. enabledRules: {}, exceptionsList: {}, disabledRules: {}".format(
            len(self.rules), len(self.exceptions), len(self.disabled_rules)))


    def load_enhancer(self):
        """Load enhancer."""
        self.enhancers['eql'] = EQLEnhancement(self.client)
        self.enhancers['indicatorMatch'] = IndicatorMatchEnhancement(self.client)
        openalert_logger.info(fr'Enhancer loaded successfully. Enhancers: {list(self.enhancers.keys())}')


    def load_actions(self):
        """Load actions."""
        self.actions['debug'] = actions.DebugAction()
        self.actions['indexer'] = actions.IndexerAction()
        self.actions['email'] = actions.EmailAction()
        openalert_logger.info(fr'Actions loaded successfully. Actions: {list(self.actions.keys())}')


    def _build_alerts(self, rule, events):
        """Helper method to add match events to alerts."""
        max_signals = rule.get('maxSignals', self.maxSignals)
        alerts = []
        for index, event in enumerate(events):
            alert = copy.deepcopy(pattern_alert)
            alert[TIMESTAMP] = ts_now()
            alert[RULE][RULE_NAME] = rule[RULE_NAME]
            alert[RULE][RULE_ID] = rule[RULE_ID]
            alert[RULE][RULE_DESCRIPTION] = rule[RULE_DESCRIPTION]
            alert[RULE][RISK_SCORE] = rule['riskScore']
            alert[RULE][SEVERITY_LABEL] = rule['severity']
            alert[RULE][RULE_TAGS] = rule[RULE_TAGS]
            alert[RULE][RULE_THREAT] = rule[RULE_THREAT]
            if '_meta' in event:
                _meta = event.pop('_meta')
                alert[METADATA][INDEX] = _meta[INDEX]
                alert[METADATA][ID] = _meta[ID]
            else:
                alert.pop(METADATA)
            alert[EVENT][MATCH] = event
            alerts.append(alert)

            if index >= max_signals - 1:
                break

        return alerts


    @staticmethod
    def _build_events(hits):
        events = []
        for hit in hits:
            if not hit['_source']:
                continue

            event = hit['_source']
            event.setdefault('_meta', {})
            event['_meta']['_index'] = hit['_index']
            event['_meta']['_id'] = hit['_id']
            events.append(event)

        return events


    def _add_exceptions_to_query(self, query: dict, exceptions_list: list):
        """Helper method to add exceptions to a query's MUST_NOT clause."""
        for exc_id in exceptions_list:
            for exception in self.exceptions.values():
                if exception['id'] != exc_id:
                    continue
                query_section = exception.get('OpenSearchQuery', {})
                query[QUERY][BOOL][MUST_NOT].extend(
                    query_section.get(QUERY, {}).get(BOOL, {}).get(MUST_NOT, [])
                )


    def run_rule_group(self, interval: int):
        """Run all rules in a group."""
        openalert_logger.info(fr'Running rule group: {interval}...')
        rules = self.grouped_rules.get(interval, {})

        # Prepare OpenSearch multi-search body
        msearch_body = []
        for rule in rules.values():
            query = rule.get('OpenSearchQuery')
            # Add exceptions to the query
            if 'exceptionsList' in rule:
                self._add_exceptions_to_query(query, rule['exceptionsList'])

            # Add rule to the multi-search body
            msearch_body.extend([
                {"index": rule['index']},
                query
            ])

        # Get data from OpenSearch
        try:
            opensearch_data = self.client.msearch(msearch_body)
        except Exception as e:
            openalert_logger.error(f"Cannot get data from OpenSearch. ERROR: {e}")
            return

        # Create alerts
        group_alerts = []
        for index, (filename, rule) in enumerate(rules.items()):
            print(filename)
            hits = opensearch_data['responses'][index]['hits']['hits']

            # Should be use multi-thread for each rule
            events = self._build_events(hits)
            if not events:
                openalert_logger.debug(f"No events found for rule: {rule['name']}")
                continue

            # Run enhancements
            if 'enhancements' in rule:
                for enhancement in rule['enhancements']:
                    enhancer = next(iter(enhancement))
                    if not events:
                        openalert_logger.debug(fr'Enhancement process has been stopped. Events are not available to run enhancer: {enhancer}')
                        break
                    events = self.enhancers[enhancer].process(events, enhancement[enhancer])

            if not events:
                openalert_logger.debug(fr'No event match after running enhancements for rule: {rule["name"]}')
                continue

            # Build alerts for rule
            rule_alerts = self._build_alerts(rule, events)
            if not rule_alerts:
                openalert_logger.debug(f"No alerts found for rule: {rule['name']}")
                continue

            # Append alerts of rule into group alerts
            group_alerts.extend(rule_alerts)

            # Execute actions on Rule
            if self.debug:
                self.actions['debug'].send(rule_alerts)
                continue

            for action in rule['actions']:
                action_name = list(action.keys())[0]  # Lấy tên action (key)
                if action_name in self.actions:
                    self.actions[action_name].send(rule_alerts, action[action_name])


        if self.debug:
            return

        # Use the Bulk API to send all alerts to OpenSearch.
        opensearch_config = {
            'client': self.client,
            'index': self.writeBackIndex
        }
        response = self.actions['indexer'].send(group_alerts, opensearch_config)
        if response:
            openalert_logger.info(f"Sent {response[0]} alerts of rules_group_{interval} to Indexer.")
        else:
            openalert_logger.error(f"Failed to send alerts of rules_group_{interval} to Indexer.")


    def clean_empty_interval_job(self, interval: int):
        """Remove interval job if it has no rules."""
        if interval in self.grouped_rules and len(self.grouped_rules[interval]) == 0:
            # Xóa group
            del self.grouped_rules[interval]
            # Xóa job
            if interval in self.jobs:
                job_id = self.jobs[interval]
                self.scheduler.remove_job(job_id)
                del self.jobs[interval]


    def ensure_job_exists(self, interval: int):
        """If an interval job doesn't exist, create it."""
        with self.jobs_lock:
            if interval not in self.jobs:
                job_id = f"group_{interval}"
                self.scheduler.add_job(self.run_rule_group, 'interval', seconds=interval, args=[interval], id=job_id,
                                       max_instances=1)
                self.jobs[interval] = job_id


    def remove_exits_rule_and_clean_job(self, file_path):
        """Remove rule and clean empty interval job."""
        if file_path not in self.rules:
            return False
        rule = self.rules[file_path]
        interval = interval_to_seconds(rule['schedule']['interval'])
        self.remove_rule(file_path)
        self.remove_rule_from_group(file_path, interval)
        self.clean_empty_interval_job(interval)
        return True


    def setup_jobs(self):
        """Create jobs for all intervals."""
        for interval in self.grouped_rules.keys():
            self.ensure_job_exists(interval)


    def start(self):
        """Start the executor."""
        self.setup_jobs()
        self.rules_watcher.start()
        self.exceptions_watcher.start()
        self.scheduler.start()


    def stop(self):
        """Stop the executor."""
        self.rules_watcher.stop()
        self.exceptions_watcher.stop()
        self.scheduler.shutdown(wait=True)

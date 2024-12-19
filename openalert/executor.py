import copy
import json
import threading
from itertools import count
from typing import Dict
from apscheduler.schedulers.background import BackgroundScheduler

from rule import RuleManager
from converter import Converter, QUERY, BOOL, MUST_NOT
from logger import openalert_logger
from opensearch_client import OpenSearchClient
from enhancements import EQLEnhancement, IndicatorMatchEnhancement
from ultils import ts_now


METADATA = 'metadata'
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

        openalert_logger.info('Loading enhancer...')
        self.enhancers = {}
        self.load_enhancer()

        openalert_logger.info('Pre-processing rules and exceptionsList...')
        self.preprocess()


    def preprocess(self):
        """Build OpenSearch query for Rule and ExceptionsList"""
        converter = Converter()
        # Get DSL_Lucene query from Rule
        self.rules = converter.convert_all(self.rules, 'rules')

        # Get DSL_Lucene query from DisabledRule
        self.disabled_rules = converter.convert_all(self.disabled_rules, 'rules')

        # Get DSL_Lucene query from ExceptionsList
        self.exceptions = converter.convert_all(self.exceptions, 'exceptionsList')

        openalert_logger.info(r"Pre-processing completed. enabledRules: {}, exceptionsList: {}, disabledRules: {}".format(
            len(self.rules), len(self.exceptions), len(self.disabled_rules)))


    def load_enhancer(self):
        """Load enhancer."""
        self.enhancers['eql'] = EQLEnhancement()
        self.enhancers['indicatorMatch'] = IndicatorMatchEnhancement()
        openalert_logger.info(fr'Enhancer loaded successfully. Enhancers: {list(self.enhancers.keys())}')


    @staticmethod
    def _add_matches(rule, hits):
        """Helper method to add match events to alerts."""
        alerts = []
        for hit in hits:
            if not hit['_source']:
                continue

            alert = copy.deepcopy(pattern_alert)
            alert[TIMESTAMP] = ts_now()
            alert[METADATA][INDEX] = hit['_index']
            alert[METADATA][ID] = hit['_id']
            alert[EVENT][MATCH] = hit['_source']
            alert[RULE][RULE_NAME] = rule['name']
            alert[RULE][RULE_ID] = rule['id']
            alert[RULE][RULE_DESCRIPTION] = rule['description']
            alert[RULE][RISK_SCORE] = rule['riskScore']
            alert[RULE][SEVERITY_LABEL] = rule['severity']
            alert[RULE][RULE_TAGS] = rule['tags']
            alert[RULE][RULE_THREAT] = rule['threat']
            alerts.append(alert)

        return alerts


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
        for index, (filename, rule) in enumerate(rules.items()):
            hits = opensearch_data['responses'][index]['hits']['hits']

            # Should be use multi-thread for each rule
            alerts = self._add_matches(rule, hits)
            if not alerts:
                continue

            if 'enhancements' in rule:
                # Run enhancements
                for enhancement in rule['enhancements']:
                    enhancer = next(iter(enhancement))
                    self.enhancers[enhancer].process(alerts, enhancement[enhancer])


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


    def setup_jobs(self):
        """Create jobs for all intervals."""
        for interval in self.grouped_rules.keys():
            self.ensure_job_exists(interval)


    def start(self):
        """Start the scheduler."""
        self.setup_jobs()
        self.scheduler.start()


    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=True)

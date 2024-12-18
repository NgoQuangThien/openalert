import json
import threading
from typing import Dict
from apscheduler.schedulers.background import BackgroundScheduler

from rule import RuleManager
from converter import Converter
from logger import openalert_logger
from opensearch_client import OpenSearchClient


class Executor(RuleManager):
    def __init__(self, rules, disabled_rules, exceptions, config):
        super().__init__(rules, disabled_rules, exceptions)

        self.debug = config.get("debug", False)
        self.writeBackIndex = config['opensearch']['writeBack']
        self.interval = config['rule']['schedule']['interval']
        self.bufferTime = config['rule']['schedule']['bufferTime']
        self.maxSignals = config['rule']['maxSignals']
        self.client = OpenSearchClient(config)

        self.scheduler = BackgroundScheduler()

        # jobs: { interval: job_id }
        self.jobs: Dict[int, str] = {}
        self.jobs_lock = threading.Lock()

        openalert_logger.info('Pre-processing rules and exceptions...')
        self.preprocess()


    def preprocess(self):
        """Build OpenSearch query for Rule and ExceptionsList"""
        converter = Converter()
        # Get DSL_Lucene query from Rule
        self.rules = converter.convert_all_rules(self.rules)

        # Get DSL_Lucene query from DisabledRule
        self.disabled_rules = converter.convert_all_rules(self.disabled_rules)

        # Get DSL_Lucene query from ExceptionsList
        self.exceptions = converter.convert_all_exceptions(self.exceptions)

        openalert_logger.info(r"Pre-processing completed. enabledRules: {}, exceptionsList: {}, disabledRules: {}".format(
            len(self.rules), len(self.exceptions), len(self.disabled_rules)))


    def run_rule_group(self, interval: int):
        """Run all rules in a group."""
        rules = self.grouped_rules.get(interval, {})

        # Generation OpenSearch m_search body
        msearch_body = []
        for filename, rule in rules.items():
            msearch_body.extend(
                [
                    {"index": rule['index']},
                    rule['OpenSearchQuery'],
                ])

        # Get data from OpenSearch
        # try:
        #     opensearch_data = self.client.msearch(msearch_body)
        # except Exception as e:
        #     openalert_logger.error(f"OpenSearch error: {e}")
        #     return

        # Create alerts
        for index, (filename, rule) in enumerate(rules.items()):
            pass



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

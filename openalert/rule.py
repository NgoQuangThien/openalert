from typing import Dict, Any

from ultils import interval_to_seconds


class RuleManager(object):
    def __init__(self, rules, disabled_rules, exceptions):
        self.rules = rules
        self.disabled_rules = disabled_rules
        self.exceptions = exceptions

        # grouped_rules: { interval: { file_path: rule_dict } }
        self.grouped_rules: Dict[int, Dict[str, Dict[str, Any]]] = {}

        # Load initial
        self.load_initial_rules()


    def load_initial_rules(self):
        """Load initial rules group."""
        for file_path in self.rules.keys():
            self.add_rule_to_group(file_path, self.rules[file_path])


    def add_rule_to_group(self, file_path: str, rule: Dict[str, Any]):
        """Add a rule to the interval group."""
        interval = interval_to_seconds(rule['schedule']['interval'])
        if interval not in self.grouped_rules:
            self.grouped_rules[interval] = {}

        self.grouped_rules[interval][file_path] = rule


    def remove_rule_from_group(self, file_path: str, interval: int):
        """Remove a rule from the interval group."""
        if interval in self.grouped_rules and file_path in self.grouped_rules[interval]:
            del self.grouped_rules[interval][file_path]
            return True
        return False

    def remove_rule(self, file_path):
        if file_path not in self.rules:
            return False
        rule = self.rules[file_path]
        interval = interval_to_seconds(rule['schedule']['interval'])
        # Delete from rules
        del self.rules[file_path]
        # Delete from rules_group
        self.remove_rule_from_group(file_path, interval)
        return True


    def remove_disabled_rule(self, file_path):
        if file_path not in self.disabled_rules:
            return False
        del self.disabled_rules[file_path]
        return True


    def remove_exception(self, file_path):
        if file_path not in self.exceptions:
            return False
        del self.exceptions[file_path]
        return True

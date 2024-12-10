class RuleType(object):
    """ The base class for a rule type.
    The class must implement add_data and add any matches to self.matches.

    :param rules: A rule configuration.
    """
    def __init__(self):
        pass


    def add_data(self, data):
        pass
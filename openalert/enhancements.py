class BaseEnhancement(object):
    """ Enhancements take a match dictionary object and modify it in some way to
    enhance an alert. These are specified in each rule under the match_enhancements option.
    Generally, the key value pairs in the match module will be contained in the alert body. """

    def __init__(self, rule):
        self.rule = rule

    def process(self, match):
        """ Modify the contents of match, a dictionary, in some way """
        raise NotImplementedError()

class EQLEnhancement(BaseEnhancement):
    """ Enhancements that modify the match dictionary based on the EQL query that was matched """
    def process(self, match):
        pass


class IndicatorMatchEnhancement(BaseEnhancement):
    """ Enhancements that modify the match dictionary based on the indicator that was matched """
    def process(self, match):
        pass

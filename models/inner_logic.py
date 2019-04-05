class DBReaderException(Exception):
    pass


class DatabaseReader(object):
    """
    returns the amount of seats available today and tomorrow on the
    flight direction
    """

    def __init__(self):
        self.answers = {"Moscow_London": [5, 10],
                        "London_Moscow": [1, 9]}

    def read(self, city_from, city_to):
        try:
            answer = self.answers.get(city_from + "_" + city_to)
        except KeyError:
            raise DBReaderException(
                "We do not support this direction")
        return answer

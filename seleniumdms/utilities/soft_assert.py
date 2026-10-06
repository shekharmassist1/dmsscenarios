class SoftAssert:
    def __init__(self):
        self.errors = []

    def check(self, condition, message):
        if not condition:
            self.errors.append(message)
        return condition

    def check_equal(self, actual, expected, label):
        return self.check(actual == expected, f"{label}: expected {expected!r}, got {actual!r}")

    def check_true(self, condition, message):
        return self.check(bool(condition), message)

    def assert_all(self):
        if self.errors:
            report = "\n".join(f"{i + 1}. {e}" for i, e in enumerate(self.errors))
            raise AssertionError(f"{len(self.errors)} soft assertion failure(s):\n{report}")

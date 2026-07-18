class SoftAssert:

    def __init__(self):
        self.errors = []

    def verify_equal(self, actual, expected, message):
        if actual != expected:
            self.errors.append(
                f"{message}\n"
                f"Expected : {expected}\n"
                f"Actual   : {actual}"
            )

    def verify_true(self, condition, message):
        if not condition:
            self.errors.append(message)

    def record_exception(self, step, exception):
        self.errors.append(
            f"{step}\n"
            f"Exception : {type(exception).__name__}\n"
            f"Message   : {exception}"
        )

    def assert_all(self):
        if self.errors:
            print("\n" + "=" * 80)
            print("VERIFICATION SUMMARY")
            print("=" * 80)

            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}\n")

            raise AssertionError("\n\n".join(self.errors))

    def execute_step(step_name, function, soft, *args, **kwargs):
        try:
            function(*args, **kwargs)
        except Exception as e:
            soft.record_exception(step_name, e)
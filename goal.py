class Goal:
    def __init__(self, target_score):
        self.target_score = target_score
        self.remaining = target_score

    def subtract(self, points):
        self.remaining = max(0, self.remaining - points)

    def is_fulfilled(self):
        return self.remaining == 0

    def get_remaining(self):
        return self.remaining

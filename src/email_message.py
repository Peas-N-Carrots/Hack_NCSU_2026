class EmailMessageModel:
    def __init__(self, from_addr, to_addr, subject, body, display_name):
        self.from_addr = from_addr
        self.to_addr = to_addr
        self.subject = subject
        self.body = body
        self.display_name = display_name
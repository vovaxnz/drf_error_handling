

class DomainError(Exception):
    code = "domain_error"
    message = "Domain error"
    http_status = 400

    def __init__(self, message=None, code=None, http_status=None):
        final_message = message or self.message
        super().__init__(final_message)
        self.message = final_message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status
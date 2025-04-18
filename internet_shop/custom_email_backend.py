import ssl

from django.core.mail.backends.smtp import EmailBackend


class CustomEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False

        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.connection = self.connection_class(self.host, self.port, context=context)
            else:
                self.connection = self.connection_class(self.host, self.port)

            if self.use_tls:
                self.connection.ehlo()
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.connection.starttls(context=context)
                self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True
        except Exception:
            if self.fail_silently:
                return False

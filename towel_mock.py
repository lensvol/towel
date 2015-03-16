from wsgiref import simple_server
import immutables
import mock_server


def main():
    app = mock_server.MockApp(immutables.REPLACE_MODULES)
    httpd = simple_server.make_server('localhost', 8029, app)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

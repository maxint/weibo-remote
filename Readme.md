Weibo Remote Control
====================

Control a remote computer through weibo.com.

After authorizing one weibo account to the control server which runs in a remote computer, you could run predefined operations by posting message and @the authorized weibo account. For example, assume @doc-server is authorized,
then "check in" operation by posting message:

> @doc-server check test_username test_password

If your are the master weibo account (see [Usage](#user-content-usage)), neither username nor password is needed.


Install Dependencies
--------------------

```shell
pip install -r requirements.txt
```


Usage
-----

Start server:
```shell
client.py <username> <passwd> --master <weibo master>
```

Help:
```shell
client.py -h
```

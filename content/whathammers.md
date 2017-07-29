Title: whathammers: a tool to get a quick overview of Apache log files
Date: 2017-05-05
Slugs: whathammers
Tags: apache
Summary: With most websites now using some form of client side analytics, we do not tend to parse and analyse Apache log files automatically any more. However for people managing web-servers they are still our first port of call when troubleshooting issues. To help quickly working out what is happening I wrote a small command line tool to parse and provide statistics out of Apache log files.

With most websites now using some form of client side analytics, we do not tend to parse and analyse Apache log files automatically any more. However for people managing web-servers they are still our first port of call when troubleshooting issues. To help quickly working out what is happening I wrote a small command line tool to parse and provide statistics out of Apache log files.

The tool, inspired by [eximstats](http://www.exim.org/exim-html-current/doc/html/spec_html/ch-exim_utilities.html#SECTmailstat), is called [**whathammers**](https://gitlab.com/aliceh75/whathammers). It can parse any Apache log file - the log format is configurable, using the same syntax as the [Apache LogFormat](https://httpd.apache.org/docs/2.2/mod/mod_log_config.html#formats) directive, so you can just copy the format from your Apache configuration.

The reports output by the tool can also be configured - though the defaults are sensible. The general idea is that, for any field available in the log file, you can output the *n* top values by number of hits or, if your log format includes the time for each request, by total time. Here is an example output, based on a real log file (but with IPs and URLs changed) using an extended log format, that shows the default reports. Note that the first thing output is the list of fields available in the log file:

```
Parsing files....
Logged fields : conn_status, remote_host, remote_logname, remote_user, request_first_line, request_header_referer, request_header_user_a
gent, request_header_user_agent__browser__family, request_header_user_agent__browser__version_string, request_header_user_agent__is_mobi
le, request_header_user_agent__os__family, request_header_user_agent__os__version_string, request_header_x_forwarded_for, request_http_v
er, request_method, request_url, request_url_fragment, request_url_hostname, request_url_netloc, request_url_password, request_url_path,
 request_url_port, request_url_query, request_url_query_dict, request_url_query_list, request_url_query_simple_dict, request_url_scheme,
 request_url_username, response_bytes_clf, server_name, status, time_received, time_received_datetimeobj, time_received_isoformat, time_
received_tz_datetimeobj, time_received_tz_isoformat, time_received_utc_datetimeobj, time_received_utc_isoformat, time_us

Top 5 remote host by hits
-------------------------
           33.33.33.33: 18496 hits (17.04% of total)
        33.333.333.333: 5090 hits (4.69% of total)
     bla.somewhere.com: 3920 hits (3.61% of total)
         333.333.33.33: 3436 hits (3.17% of total)
and.somewhere.else.com: 2567 hits (2.36% of total)

Top 5 remote host by total time
-------------------------------
           33.33.33.33: 30575.46 seconds (21.88% of total)
     bla.somewhere.com: 4010.18 seconds (2.87% of total)
        33.333.333.333: 3932.08 seconds (2.81% of total)
         333.333.33.33: 3880.73 seconds (2.78% of total)
and.somewhere.else.com: 3581.93 seconds (2.56% of total)

Top 5 user agent by hits
------------------------
Mozilla/5.0 (compatible; MJ12bot/v1.4...: 26365 hits (24.29% of total)
Mozilla/4.0 (compatible; MSIE 9.0; Wi...: 11216 hits (10.33% of total)
Mozilla/5.0 (Windows NT 6.3; Win64; x...: 9522 hits (8.77% of total)
Mozilla/5.0 (Macintosh; Intel Mac OS ...: 8154 hits (7.51% of total)
Mozilla/5.0 (compatible; Googlebot/2....: 4596 hits (4.23% of total)

Top 5 user agent by total time
------------------------------
Mozilla/5.0 (compatible; MJ12bot/v1.4...: 38073.62 seconds (27.24% of total)
Mozilla/5.0 (Macintosh; Intel Mac OS ...: 18340.86 seconds (13.12% of total)
Mozilla/4.0 (compatible; MSIE 9.0; Wi...: 11810.71 seconds (8.45% of total)
Mozilla/5.0 (Windows NT 6.3; Win64; x...: 11578.16 seconds (8.28% of total)
Mozilla/5.0 (compatible; Googlebot/2....: 7003.51 seconds (5.01% of total)

Top 5 request_url_path by hits
------------------------------
                /a/path: 14397 hits (13.26% of total)
/another/path/or/sorts/: 6580 hits (6.06% of total)
                      /: 5942 hits (5.47% of total)
     /paths/everywhere/: 4133 hits (3.81% of total)
       /the/super/path/: 3597 hits (3.31% of total)

time_received by hits, 5 slices
-------------------------------
2017-04-23 04:14:29: ---------------- (12483 hits)
2017-04-23 21:13:08: ------------------------- (18810 hits)
2017-04-24 14:11:47: -------------------------- (19702 hits)
2017-04-25 07:10:26: ------------------------------------- (27745 hits)
2017-04-26 00:09:05: ---------------------------------------- (29814 hits)

time_received by time per hit, 5 slices
---------------------------------------
2017-04-23 04:14:29: --------------------------------- (1.43 seconds)
2017-04-23 21:13:08: ------------------------------- (1.30 seconds)
2017-04-24 14:11:47: ---------------------- (955.42 miliseconds)
2017-04-25 07:10:26: ------------------------ (1.03 seconds)
2017-04-26 00:09:05: ---------------------------------------- (1.68 seconds)
```

More advanced functionality can easily be achieved by combining our usual set of command line tools - for example you can simply filter out entries before analysis by using `grep -v`:

```
cat access.log | grep -v 111.111.111.111 | whathammers
``` 

[Usage instructions and the source code are on Gitlab](https://gitlab.com/aliceh75/whathammers) and **whathammers** is also available as a [Python package on pypi.python.org](https://pypi.python.org/pypi/whathammers).

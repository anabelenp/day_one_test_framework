# DLP JMeter Tests

This folder contains JMeter test plans focused on DLP (Data Loss Prevention) scan endpoints.

Files:
- `dlp_scan_load_test.jmx` - DLP-focused load test that sends POST requests to `/api/v2/dlp/scan-file`.

Usage:

Command-line example:
```
# Run with default parameters
jmeter -n -t tests/performance/jmeter/dlp_scan_load_test.jmx \
       -Jbase_url=http://localhost:8080 \
       -Jusers=50 -Jramp_time=60 -Jduration=300 \
       -l reports/dlp_jmeter_results.jtl \
       -e -o reports/dlp_jmeter_html_report
```

Notes:
- The test plan uses simple JSON payloads for scanning. Adjust the body or switch to multipart file uploads if your API requires true file multipart uploads.
- Set `base_url`, `users`, `ramp_time`, and `duration` via `-J` properties when running headless.

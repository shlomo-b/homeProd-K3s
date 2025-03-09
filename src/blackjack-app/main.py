import time
import psutil
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from flask import Flask, Response, render_template, request, g

# Initialize Flask app and set the correct template folder
app = Flask(__name__, template_folder='')  # Change this path if necessary

# Create Prometheus metrics
GAMES_PLAYED = Counter('games_played', 'Number of Blackjack games played')
SITE_VISITS = Counter('site_visits', 'Number of visits to the Blackjack site')

# System metrics
CPU_USAGE = Gauge('cpu_usage_percent', 'Current CPU usage in percent')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Current memory usage in bytes')
NETWORK_IO_COUNTERS = Gauge('network_io_bytes', 'Network I/O counters', ['direction'])

# HTTP metrics
HTTP_REQUESTS = Counter('http_requests_total', 'Total number of HTTP requests', ['method', 'endpoint', 'status_code'])
HTTP_REQUEST_DURATION = Histogram('http_request_duration_seconds', 'Histogram of HTTP request durations',
                                  ['method', 'endpoint'])


# Before and after request hooks to track request durations and counts
@app.before_request
def track_request_start():
    # Record the start time of the request
    g.start_time = time.time()


@app.after_request
def track_request_end(response):
    # Measure request duration
    if hasattr(g, 'start_time'):
        request_duration = time.time() - g.start_time
        HTTP_REQUEST_DURATION.labels(method=request.method, endpoint=request.path).observe(request_duration)

    # Count the request
    HTTP_REQUESTS.labels(method=request.method, endpoint=request.path, status_code=response.status_code).inc()

    return response


# Route for home page
@app.route('/')
def index():
    return render_template('blackjack.html')


# Route for presentation page
@app.route('/presentation')
def presentation():
    return render_template('presentation.html')


# Metrics endpoint to expose Prometheus metrics
@app.route('/metrics')
def metrics():
    # Update system metrics before serving
    CPU_USAGE.set(psutil.cpu_percent())
    MEMORY_USAGE.set(psutil.virtual_memory().used)
    net_io = psutil.net_io_counters()
    NETWORK_IO_COUNTERS.labels('in').set(net_io.bytes_recv)
    NETWORK_IO_COUNTERS.labels('out').set(net_io.bytes_sent)

    # Return Prometheus metrics in the required format
    return Response(generate_latest(), mimetype='text/plain')


# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

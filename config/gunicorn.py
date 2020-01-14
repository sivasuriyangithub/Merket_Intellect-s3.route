import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
timeout = 180
graceful_timeout = 500

import logging.config

from pythonjsonlogger.jsonlogger import JsonFormatter

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'standard': {
            'format': '[%(process)d] %(asctime)s [%(levelname)s] %(name)s: %(message)s',
        },
        'json_formatter': {
            '()': JsonFormatter,
            'fmt': '%(process)d %(asctime)s %(levelname)s %(name) %(message)s',
        },
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'DEBUG',
        },
        'json_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'json_formatter',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        '': {
            'handlers': ['json_handler'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'aiohttp': {
            'handlers': ['json_handler'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'pika': {
            'handlers': ['json_handler'],
            'level': 'INFO',
            'propagate': True,
        },
        # 'producer': {
        #     'handlers': ['json_handler'],
        #     'level': 'DEBUG',
        #     'propagate': False,
        # },
        # 'consumer': {
        #     'handlers': ['json_handler'],
        #     'level': 'DEBUG',
        #     'propagate': False,
        # },
        # 'werkzeug': {
        #     'handlers': ['json_handler'],
        #     'level': 'DEBUG',
        #     'propagate': False,
        # },
        # 'connexion': {
        #     'handlers': ['default'],
        #     'level': 'CRITICAL',
        #     'propagate': True,
        # },
        # 'swagger_spec_validator': {
        #     'handlers': ['default'],
        #     'level': 'CRITICAL',
        #     'propagate': True,
        # },
    }
})

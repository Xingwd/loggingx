# loggingx

logging拓展功能模块。

[Installation](#installation) |  [Usage](#usage)
***

## Installation

安装loggingx，只需要执行：

``` bash
pip install loggingx
```

loggingx部分功能需要依赖消息队列，需要安装相关依赖，可以通过以下命令安装必要的依赖：

``` bash
pip install "loggingx[queue]"
```

## Usage

loggingx在使用上基本和logging一致。

### handlers.RedisStreamHandler

将日志消息发布到redis stream消息队列，配合[handlers.RedisStreamListener](#handlersredisstreamlistener)可以解决多进程写日志文件不安全的问题。

``` python
# 示例一：直接使用

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)
rsh = RedisStreamHandler('redis://redis:6379/0')
logger.addHandler(rsh)

# 示例二：在配置文件中使用
LOGGING_CONFIG = {
   'version': 1,
   'disable_existing_loggers': False,
   'formatters': {
      'verbose': {
         'format': '%(asctime)s.%(msecs)03d %(levelname)-8s %(processName)s:%(threadName)s %(pathname)s:%(lineno)d - %(message)s',
         'datefmt': '%Y-%m-%d %H:%M:%S'
      },
      'simple': {
         'format': '{name:s}: {asctime:s} {levelname} {message}',
         'style': '{',
         'datefmt': '%Y-%m-%d %H:%M:%S'
      },
   },
   'handlers': {
      'console': {
         'class': 'logging.StreamHandler',
         'level': 'INFO',
         'formatter': 'simple'
      },
      'redis_stream': {
         'class': 'loggingx.handlers.RedisStreamHandler',
         'level': 'INFO',
         'redis_url': 'redis://redis:6379/0'
      }
   },
   'loggers': {
      'cloud': {
         'handlers': ['console'],
         'propagate': True,
      },
      'cloud.request': {
         'handlers': ['redis_stream'],
         'level': 'INFO',
         'propagate': True,
      }
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```

在多进程服务中使用RedisStreamHandler，然后单独启动一个进程运行RedisStreamListener，可以保证日志消息完整传递到下游处理器。

完整示例可以参考[examples](examples/redis_stream_handler.py)。

### handlers.RedisStreamListener

消费redis stream消息队列的日志消息，传递到下游handlers。

RedisStreamListener不属于处理器，需要和[handlers.RedisStreamHandler](#handlersredisstreamhandler)配合工作。

``` python
# 创建TimedRotatingFileHandler实例
fh = logging.handlers.TimedRotatingFileHandler('logs/cloud.log', when='M', backupCount=5)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
# 使用RedisStreamListener消费RedisStreamHandler消息，传递到TimedRotatingFileHandler
rsl = RedisStreamListener('redis://redis:6379/0', fh)
rsl.start()
```

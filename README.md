# loggingx

logging拓展功能模块。

[Installation](#installation) |  [Usage](#usage)
---------------------------------------------

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
logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)
rlh = RedisStreamHandler(redis_url)
logger.addHandler(rlh)
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
rsl = RedisStreamListener(redis_url, fh)
rsl.start()
```

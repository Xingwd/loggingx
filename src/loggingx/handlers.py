import redis
from typing import Union
from logging import LogRecord, makeLogRecord
from logging.handlers import QueueHandler, QueueListener


DEFAULT_REDIS_STREAM_KEY = 'log'  # Redis stream消息队列默认key


class RedisStreamHandler(QueueHandler):
    """
    Redis stream处理器，发布logging日志到redis stream消息队列。
    """

    def __init__(
        self,
        redis_url: str,
        redis_stream_key: str = DEFAULT_REDIS_STREAM_KEY,
        **redis_kwargs
    ):
        """
        初始化一个实例。

        Args:
            redis_url (str): Redis URL，redis的连接字符串。
            redis_stream_key (str, optional): Redis stream类型的key。默认是 DEFAULT_REDIS_STREAM_KEY。
            **redis_kwargs : redis.Redis.from_url()方法的 **kwargs 参数。
        """

        self.redis_stream_key = redis_stream_key

        r = redis.Redis.from_url(redis_url, **redis_kwargs)

        super().__init__(r)

    def enqueue(self, record: LogRecord):
        """
        Override QueueHandler.enqueue(self, record)方法。
        发布日志消息到redis stream消息队列。

        Args:
            record (LogRecord): LogRecord实例。
        """
        # Redis stream会对消息进行encode，需要移除value为None的属性
        value = {k:v for k, v in record.__dict__.items() if v is not None}
        self.queue.xadd(self.redis_stream_key, value)


class RedisStreamListener(QueueListener):
    """
    RedisStreamHandler的侦听器，消费redis stream消息队列的日志消息，转发到下游handlers。
    """

    def __init__(
        self,
        redis_url: str,
        *handlers,
        respect_handler_level: bool = False,
        redis_stream_key: str = DEFAULT_REDIS_STREAM_KEY,
        **redis_kwargs
    ):
        """
        初始化一个实例。

        Args:
            redis_url (str): Redis URL，redis的连接字符串。
            *handlers : QueueListener类的 *handlers 参数。
            respect_handler_level (bool, optional): QueueListener类的 respect_handler_level 参数。 默认是 False.
            redis_stream_key (str, optional): Redis stream类型的key。默认是 DEFAULT_REDIS_STREAM_KEY。
            **redis_kwargs : redis.Redis.from_url()方法的 **kwargs 参数。
        """

        self.redis_stream_key = redis_stream_key

        # redis stream消息队列消费者初始id，0表示从最早的消息开始消费
        self.redis_stream_id = 0

        # stop方法哨兵消息key和value
        self.stop_sentinel_key = 'sentinel_key'
        self.stop_sentinel_value = 'sentinel_value'

        r = redis.Redis.from_url(redis_url, **redis_kwargs)
        self.redis_encoding = r.get_encoder().encoding
        self.redis_encoding_errors = r.get_encoder().encoding_errors

        super().__init__(r, *handlers, respect_handler_level=respect_handler_level)

    def dequeue(self, block) -> Union[dict[bytes, bytes], None]:
        """
        Override QueueHandler.dequeue(self, block)方法。
        消费redis stream消息队列的日志消息。

        Args:
            block (bool): 是否阻塞。

        Returns:
            Union[dict[bytes, bytes], None]: LogRecord实例属性字典，key和value都是bytes类型。
        """

        # 判断是否阻塞，0表示永久阻塞
        xread_block = 0 if block else None
        record = None
        # 消费Redis stream消息队列，默认从最早的记录进行消费
        msgs = self.queue.xread(
            streams={self.redis_stream_key: self.redis_stream_id},
            count=1,
            block=xread_block
        )
        if msgs:
            for id, msg in msgs[0][1]:
                self.redis_stream_id = id
                # 判断哨兵消息
                if msg.get(self.redis_encode(self.stop_sentinel_key)) != self.redis_encode(self.stop_sentinel_value):
                    record = msg
                # 删除已消费的数据
                self.queue.xdel(self.redis_stream_key, id)
        return record

    def redis_encode(self, value: str) -> bytes:
        """
        使用redis连接实例的编码参数进行编码。

        Args:
            value (str): 需要编码的字符串。

        Returns:
            bytes: 编码结果。
        """

        return value.encode(self.redis_encoding, self.redis_encoding_errors)

    def redis_decode(self, value: bytes) -> str:
        """
        使用redis连接实例的编码参数进行解码。

        Args:
            value (bytes): 需要解码的bytes字符串。

        Returns:
            str: 解码结果。
        """

        return value.decode(self.redis_encoding, self.redis_encoding_errors)

    def prepare(self, record: dict[bytes, bytes]) -> LogRecord:
        """
        Override QueueHandler.prepare(self, record)方法。
        准备日志消息，将从redis stream消息队列消费的消息转换成LogRecord实例。

        Args:
            record (dict[bytes, bytes]): 从redis stream消息队列消费的消息。

        Returns:
            LogRecord: LogRecord实例。
        """

        decode_record = {}
        # 解码
        for k, v in record.items():
            decode_k, decode_v = self.redis_decode(k), self.redis_decode(v)
            if decode_k in ['levelno', 'lineno', 'thread', 'process']:
                decode_v = int(decode_v)
            elif decode_k in ['created', 'msecs', 'relativeCreated']:
                decode_v = float(decode_v)
            decode_record[decode_k] = decode_v

        # 根据日志属性生成LogRecord实例
        record = makeLogRecord(decode_record)
        return record

    def enqueue_sentinel(self):
        """
        Override QueueHandler.enqueue_sentinel(self)方法。
        发布哨兵消息，用于优雅的关闭侦听器线程。
        """
        self.queue.xadd(
            self.redis_stream_key,
            {self.stop_sentinel_key: self.stop_sentinel_value}
        )

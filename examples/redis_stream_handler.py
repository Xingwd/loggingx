import argparse
import time
import logging
from loggingx.handlers import RedisStreamHandler, RedisStreamListener


def main(redis_url):
    # 添加RedisStreamHandler
    logger = logging.getLogger('test')
    logger.setLevel(logging.DEBUG)
    rlh = RedisStreamHandler(redis_url)
    logger.addHandler(rlh)

    # 创建TimedRotatingFileHandler实例
    fh = logging.handlers.TimedRotatingFileHandler('logs/cloud.log', when='M', backupCount=5)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # 使用RedisStreamListener消费RedisStreamHandler消息，传递到TimedRotatingFileHandler
    rsl = RedisStreamListener(redis_url, fh)
    rsl.start()

    for i in range(10):
        print(rsl._thread, rsl._thread.is_alive())
        logger.debug('This message should go to the log file')
        logger.info('So should this')
        logger.warning('And this, too')
        logger.error('And non-ASCII stuff, too, like Øresund and Malmö')
        time.sleep(10)
    # 关闭线程
    rsl.stop()
    print(rsl._thread)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='RedisStreamHandlerExample', description='RedisStreamHandler example.')
    parser.add_argument('--redis-url', default='redis://localhost:6379/0', help='redis url.')
    args = parser.parse_args()

    main(args.redis_url)

    # 保证进程持续运行
    # while True:
    #     pass

import multiprocessing
import engine
import common
from engine import *
from engine.downloader import download, check
from common import logger
from common.event import Event
from engine.plugins.base_adapter import UploadBase
from engine.uploader import upload

# 初始化事件管理器
event_manager = common.event.EventManager(context)


@event_manager.register(DOWNLOAD, block=True)
def process(name, url):
    try:
        data = {"url": url, "date": common.time_now()}
        p = multiprocessing.Process(target=download, args=(name, url))
        p.start()
        p.join()
        # download(name, url)
        upload("bili_web", name, data)
    finally:
        return Event(BE_MODIFIED, args=(url,))


@event_manager.register(UPLOAD, block=True)
def process_upload(name, url):
    try:
        data = {"url": url, "date": common.time_now()}
        upload("bili_web", name, data)
    finally:
        return Event(BE_MODIFIED, args=(url,))


@event_manager.server()
class KernelFunc:
    def __init__(self, urls, url_status: dict):
        self.urls = urls
        self.url_status = url_status
        self.__raw_streamer_status = url_status.copy()

    @event_manager.register(CHECK, block=True)
    def batch_check(self):
        live = check(self.urls, "batch")
        return Event(CHECK_UPLOAD, args=(live,)), Event(TO_MODIFY, args=(live,))

    @event_manager.register(CHECK, block=True)
    def singleton_check(self):
        live = check(self.urls, "single")
        return Event(TO_MODIFY, args=(live,))

    @event_manager.register(TO_MODIFY)
    def modify(self, live_m):
        if not live_m:
            return logger.debug('无人直播')
        live_d = {}
        for live in live_m:
            if self.url_status[live] == 1:
                logger.debug('已开播正在下载')
            else:
                name = inverted_index[live]
                logger.debug(f'{name}刚刚开播，去下载')
                event_manager.send_event(Event(DOWNLOAD, args=(name, live)))

            live_d[live] = 1
        self.url_status.update(live_d)
        # self.url_status = {**self.__raw_streamer_status, **live_d}

    def free(self, list_url):
        status_num = list(map(lambda x: self.url_status.get(x), list_url))
        # if 1 in status_num or 2 in status_num:
        #     return False
        # else:
        #     return True
        return not (1 in status_num or 2 in status_num)

    @event_manager.register(CHECK_UPLOAD)
    def free_upload(self, _urls):
        logger.debug(_urls)
        for title, v in engine.streamer_url.items():
            url = v[0]
            if self.free(v) and UploadBase.filter_file(title):
                event_manager.send_event(Event(UPLOAD, args=(title, url)))
                self.url_status[url] = 2

    @event_manager.register(BE_MODIFIED)
    def revise(self, url):
        if url:
            # 更新字典
            # url_status = {**url_status, **{url: 0}}
            self.url_status.update({url: 0})

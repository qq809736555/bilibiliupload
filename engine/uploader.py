from common import logger
from common.decorators import Plugin


def upload(platform, index, data):
    """
    上传入口
    :param platform:
    :param index:
    :param data: 现在需包含内容{url,date} 完整包含内容{url,date,format_title}
    :return:
    """
    try:
        return Plugin.upload_plugins.get(platform)(index, data).start()
    except:
        logger.exception("Uncaught exception:")
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
解析歌词文件
'''

import re
import traceback

from kuwo.log import logger

try:
    from ply import lex
except ImportError:
    logger.debug(traceback.format_exc())

__all__ = ['parse_lrc']

def parse_lrc(lrc_txt):
    '''解析歌词'''
    try:
        return parser_lex(lrc_txt)
    except lex.LrcError:
        logger.error(traceback.format_exc())
    except NameError:
        # lex is unavailable
        pass
    finally:
        return parser_re(lrc_txt)

def time_tag_to_nano(time_tags):
    '''将时间标记转为纳秒'''
    if isinstance(time_tags, str):
        mm = time_tags[:2]
        ss = time_tags[3:5]
        ml = time_tags[6:]
    else:
        mm, ss, ml = time_tags
    if not ml:
        curr_time = int(mm) * 60 + int(ss)
    else:
        curr_time = int(mm) * 60 + int(ss) + float(ml)
    return int(curr_time * 10 ** 9)

def sort_lrc_tags(lrc_obj):
    '''从小到大对时间标记进行排序'''
#    lrc_obj = [[-4, ''], [-3, ''], [-2, ''], ] + lrc_obj
#    last_time = lrc_obj[-1][0]
#    if last_time <= 0:
#        logger.error('LrcParser.parser_re(): %s.' % last_time)
#        return None
#    for i in range(last_time, last_time * 2 + 5, last_time // 4 + 1):
#        lrc_obj.append([i, ''])
    return sorted(lrc_obj, key=lambda item: item[0])

def parser_lex(lrc_txt):
    tokens = (
        'TIME',
        'STRING',
    )

    def t_TIME(token):
        r'\[\d{2}:\d{2}(?:\.\d{1,3})\]'
        token.value = token.value[1:-1]
        return token

    def t_STRING(token):
        r'[^\[\]\n]+'
        return token

    def t_newline(token):
        r'\n'
        token.lexer.lineno += 1

    def t_error(token):
        logger.debug('LrcParser.parser_lex.t_error: %s', token.value)

    lrc_lex = lex.lex()
    lrc_lex.input(lrc_txt)
    lrc_obj = []
    time_tags = []
    for token in lrc_lex:
        if token.type == 'TIME':
            time_tags.append(token.value)
        else:
            for time_tag in time_tags:
                lrc_obj.append([time_tag_to_nano(time_tag), token.value])
            time_lst.clear()
    return sort_lrc_tags(lrc_obj)

def parser_re(lrc_txt):
    '''使用正则来解析lrc, 但有可能会出错'''
    lines = lrc_txt.split('\n')
    lrc_obj = []

    reg_time = re.compile('\[([0-9]{2}):([0-9]{2})(\.[0-9]{1,3})?\]')
    for line in lines:
        offset = 0
        match = reg_time.match(line)
        tags = []
        while match:
            time = time_tag_to_nano(match.groups())
            tags.append(time)
            offset = match.end()
            match = reg_time.match(line, offset)
        content = line[offset:]
        for tag in tags:
            lrc_obj.append([tag, content])
    return sort_lrc_tags(lrc_obj)

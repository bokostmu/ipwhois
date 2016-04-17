# Copyright (c) 2013, 2014, 2015, 2016 Philip Hane
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# CLI python script interface for ipwhois lookups and utilities.

import argparse
from os import path
from ipwhois import IPWhois
from ipwhois.hr import (HR_ASN, HR_RDAP, HR_RDAP_COMMON, HR_WHOIS)

try:  # pragma: no cover
    from urllib.request import (ProxyHandler,
                                build_opener)
except ImportError:  # pragma: no cover
    from urllib2 import (ProxyHandler,
                         build_opener)

# CLI ANSI rendering
ANSI = {
    'end': '\033[0m',
    'b': '\033[1m',
    'ul': '\033[4m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'cyan': '\033[36m'
}

# Color definitions for sub lines
COLOR_DEPTH = {
    '0': ANSI['green'],
    '1': ANSI['yellow'],
    '2': ANSI['red'],
    '3': ANSI['cyan']
}

# Line formatting, keys ending in C are colorized versions.
LINES = {
    '1': '>> ',
    '2': '>> >>> ',
    '3': '>> >>> >>>> ',
    '4': '>> >>> >>>> >>>>> ',
    '1C': '{0}>>{1} '.format(COLOR_DEPTH['0'], ANSI['end']),
    '2C': '{0}>>{1} >>>{2} '.format(
        COLOR_DEPTH['0'], COLOR_DEPTH['1'], ANSI['end']
    ),
    '3C': '{0}>>{1} >>>{2} >>>>{3} '.format(
        COLOR_DEPTH['0'], COLOR_DEPTH['1'], COLOR_DEPTH['2'], ANSI['end']
    ),
    '4C': '{0}>>{1} >>>{2} >>>>{3} >>>>>{4} '.format(
        COLOR_DEPTH['0'], COLOR_DEPTH['1'], COLOR_DEPTH['2'], COLOR_DEPTH['3'],
        ANSI['end']
    ),
}

# Setup the arg parser.
parser = argparse.ArgumentParser(
    description='ipwhois CLI interface'
)
parser.add_argument(
    '--whois',
    action='store_true',
    help='Retrieve whois data via legacy Whois (port 43) instead of RDAP '
         '(default).'
)

# Output options
group = parser.add_argument_group('Output options')
group.add_argument(
    '--hr',
    action='store_true',
    help='If set, returns results with human readable key translations.'
)
group.add_argument(
    '--show_name',
    action='store_true',
    help='If this and --hr are set, the key name is shown in parentheses after'
         'its short value'
)
group.add_argument(
    '--colorize',
    action='store_true',
    help='If set, colorizes the output using ANSI. Should work in most '
         'platform consoles.'
)

# IPWhois settings (common)
group = parser.add_argument_group('IPWhois settings')
group.add_argument(
    '--timeout',
    type=int,
    default=5,
    metavar='TIMEOUT',
    help='The default timeout for socket connections in seconds.'
)
group.add_argument(
    '--proxy_http',
    type=str,
    nargs=1,
    default=[None],
    metavar='"PROXY_HTTP"',
    help='The proxy HTTP address passed to request.ProxyHandler. User auth'
         'can be passed like "http://user:pass@192.168.0.1:80"',
    required=False
)
group.add_argument(
    '--proxy_https',
    type=str,
    nargs=1,
    default=[None],
    metavar='"PROXY_HTTPS"',
    help='The proxy HTTPS address passed to request.ProxyHandler. User auth'
         'can be passed like "https://user:pass@192.168.0.1:443"',
    required=False
)
group.add_argument(
    '--allow_permutations',
    action='store_true',
    help='Use additional methods if DNS lookups to Cymru fail.'
)

# Common (RDAP & Legacy Whois)
group = parser.add_argument_group('Common settings (RDAP & Legacy Whois)')
group.add_argument(
    '--inc_raw',
    action='store_true',
    help='Include the raw whois results in the output.'
)
group.add_argument(
    '--retry_count',
    type=int,
    default=3,
    metavar='RETRY_COUNT',
    help='The number of times to retry in case socket errors, timeouts, '
         'connection resets, etc. are encountered.'
)
group.add_argument(
    '--asn_alts',
    type=str,
    nargs=1,
    default=[None],
    metavar='"ASN_ALTS"',
    help='A comma delimited list of additional lookup types to attempt if the '
         'ASN dns lookup fails. Allow permutations must be enabled. '
         'Defaults to all: "whois,http"'
)

# RDAP
group = parser.add_argument_group('RDAP settings')
group.add_argument(
    '--depth',
    type=int,
    default=0,
    metavar='COLOR_DEPTH',
    help='If not --whois, how many levels deep to run RDAP queries when '
         'additional referenced objects are found.'
)
group.add_argument(
    '--excluded_entities',
    type=str,
    nargs=1,
    default=[None],
    metavar='"EXCLUDED_ENTITIES"',
    help='If not --whois, a comma delimited list of entity handles to not '
         'perform lookups.'
)
group.add_argument(
    '--bootstrap',
    action='store_true',
    help='If not --whois, performs lookups via ARIN bootstrap rather than '
         'lookups based on ASN data. ASN lookups are not performed and no '
         'output for any of the asn* fields is provided.'
)
group.add_argument(
    '--rate_limit_timeout',
    type=int,
    default=120,
    metavar='RATE_LIMIT_TIMEOUT',
    help='If not --whois, the number of seconds to wait before retrying when '
         'a rate limit notice is returned via rdap+json.'
)

# Legacy Whois
group = parser.add_argument_group('Legacy Whois settings')
group.add_argument(
    '--get_referral',
    action='store_true',
    help='If --whois, retrieve referral whois information, if available.'
)
group.add_argument(
    '--extra_blacklist',
    type=str,
    nargs=1,
    default=[None],
    metavar='"EXTRA_BLACKLIST"',
    help='If --whois, A list of blacklisted whois servers in addition to the '
         'global BLACKLIST.'
)
group.add_argument(
    '--ignore_referral_errors',
    action='store_true',
    help='If --whois, ignore and continue when an exception is encountered on '
         'referral whois lookups.'
)
group.add_argument(
    '--field_list',
    type=str,
    nargs=1,
    default=[None],
    metavar='"FIELD_LIST"',
    help='If --whois, a list of fields to parse: '
         '[\'name\', \'handle\', \'description\', \'country\', \'state\', '
         '\'city\', \'address\', \'postal_code\', \'emails\', \'created\', '
         '\'updated\']'
)

# Input (required)
group = parser.add_argument_group('Input (Required)')
group.add_argument(
    '--addr',
    type=str,
    nargs=1,
    metavar='"IP"',
    help='An IPv4 or IPv6 address as a string.',
    required=True
)

# Get the args
args = parser.parse_args()

# Get the current working directory.
CUR_DIR = path.dirname(__file__)


def generate_output(line='0', short=None, name=None, value=None,
                    is_parent=False, colorize=True):

    # TODO: so ugly
    output = '{0}{1}{2}{3}{4}{5}{6}{7}\n'.format(
        LINES['{0}{1}'.format(line, 'C' if colorize else '')] if (
            line in LINES.keys()) else '',
        COLOR_DEPTH[line] if (colorize and line in COLOR_DEPTH) else '',
        ANSI['b'],
        short if short is not None else (
            name if (name is not None) else ''
        ),
        '' if (name is None or short is None) else ' ({0})'.format(
            name),
        '' if (name is None and short is None) else ': ',
        ANSI['end'] if colorize else '',
        '' if is_parent else value
    )

    return output


class IPWhoisCLI:

    def __init__(
        self,
        addr,
        timeout,
        proxy_http,
        proxy_https,
        allow_permutations
    ):

        self.addr = addr
        self.timeout = timeout

        handler_dict = None
        if proxy_http is not None:

            handler_dict = {'http': proxy_http}

        if proxy_https is not None:

            if handler_dict is None:

                handler_dict = {'https': proxy_https}

            else:

                handler_dict['https'] = proxy_https

        if handler_dict is None:

            self.opener = None
        else:

            handler = ProxyHandler(handler_dict)
            self.opener = build_opener(handler)

        self.allow_permutations = allow_permutations

        self.obj = IPWhois(address=self.addr,
                           timeout=self.timeout,
                           proxy_opener=self.opener,
                           allow_permutations=self.allow_permutations)

    def generate_output_header(self, query_type='RDAP'):

        output = '\n{0}{1}{2} query for {3}:{4}\n\n'.format(
            ANSI['ul'],
            ANSI['b'],
            query_type,
            self.obj.address_str,
            ANSI['end']
        )

        return output

    def generate_output_newline(self, line='0', colorize=True):
        return generate_output(
            line=line,
            is_parent=True,
            colorize=colorize
        )

    def generate_output_asn(self, json_data=None, hr=True, show_name=False,
                            colorize=True):

        if json_data is None:
            json_data = {}

        # Python 2.6 doesn't support set literal expressions, use explicit
        # set() instead.
        keys = set(['asn', 'asn_cidr', 'asn_country_code', 'asn_date',
                    'asn_registry']).intersection(json_data)

        output = ''

        for key in keys:

            output += generate_output(
                line='0',
                short=HR_ASN[key]['_short'] if hr else key,
                name=HR_ASN[key]['_name'] if (hr and show_name) else None,
                value=(json_data[key] if (
                    json_data[key] is not None and
                    len(json_data[key]) > 0 and
                    json_data[key] != 'NA') else 'None'),
                colorize=colorize
            )

        return output

    def generate_output_entities(self, json_data=None, hr=True,
                                 show_name=False, colorize=True):

        output = ''
        short = HR_RDAP['entities']['_short'] if hr else 'entities'
        name = HR_RDAP['entities']['_name'] if (hr and show_name) else None

        output += generate_output(
            line='0',
            short=short,
            name=name,
            is_parent=False if (json_data is None or
                                json_data['entities'] is None) else True,
            value='None' if (json_data is None or
                             json_data['entities'] is None) else None,
            colorize=colorize
        )

        if json_data is not None:

            for ent in json_data['entities']:

                output += generate_output(
                    line='1',
                    value=ent,
                    colorize=colorize
                )

        return output

    def generate_output_events(self, source, key, val, line='2', hr=True,
                               show_name=False, colorize=True):

        output = generate_output(
            line=line,
            short=HR_RDAP[source][key]['_short'] if hr else key,
            name=HR_RDAP[source][key]['_name'] if (hr and show_name) else None,
            is_parent=False if (val is None or
                                len(val) == 0) else True,
            value='None' if (val is None or
                             len(val) == 0) else None,
            colorize=colorize
        )

        if val is not None:

            count = 0
            for item in val:

                try:
                    action = item['action']
                except KeyError:
                    action = None

                try:
                    timestamp = item['timestamp']
                except KeyError:
                    timestamp = None

                try:
                    actor = item['actor']
                except KeyError:
                    actor = None

                if count > 0:
                    output += generate_output(
                        line=str(int(line)+1),
                        is_parent=True,
                        colorize=colorize
                    )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['action'][
                        '_short'] if hr else 'action',
                    name=HR_RDAP_COMMON[key]['action'][
                        '_name'] if (hr and show_name) else None,
                    value=action,
                    colorize=colorize
                )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['timestamp'][
                        '_short'] if hr else 'timestamp',
                    name=HR_RDAP_COMMON[key]['timestamp'][
                        '_name'] if (hr and show_name) else None,
                    value=timestamp,
                    colorize=colorize
                )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['actor'][
                        '_short'] if hr else 'actor',
                    name=HR_RDAP_COMMON[key]['actor'][
                        '_name'] if (hr and show_name) else None,
                    value=actor,
                    colorize=colorize
                )

                count += 1

        return output

    def generate_output_list(self, source, key, val, line='2', hr=True,
                             show_name=False, colorize=True):

        output = generate_output(
            line=line,
            short=HR_RDAP[source][key]['_short'] if hr else key,
            name=HR_RDAP[source][key]['_name'] if (hr and show_name) else None,
            is_parent=False if (val is None or
                                len(val) == 0) else True,
            value='None' if (val is None or
                             len(val) == 0) else None,
            colorize=colorize
        )

        if val is not None:
            for item in val:
                output += generate_output(
                    line=str(int(line)+1),
                    value=item,
                    colorize=colorize
                )

        return output

    def generate_output_notices(self, source, key, val, line='1', hr=True,
                                show_name=False, colorize=True):

        output = generate_output(
            line=line,
            short=HR_RDAP[source][key]['_short'] if hr else key,
            name=HR_RDAP[source][key]['_name'] if (hr and show_name) else None,
            is_parent=False if (val is None or
                                len(val) == 0) else True,
            value='None' if (val is None or
                             len(val) == 0) else None,
            colorize=colorize
        )

        if val is not None:

            count = 0
            for item in val:

                title = item['title']
                description = item['description']
                links = item['links']

                if count > 0:
                    output += generate_output(
                        line=str(int(line)+1),
                        is_parent=True,
                        colorize=colorize
                    )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['title']['_short'] if hr else (
                        'title'),
                    name=HR_RDAP_COMMON[key]['title']['_name'] if (
                        hr and show_name) else None,
                    value=title,
                    colorize=colorize
                )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['description'][
                        '_short'] if hr else 'description',
                    name=HR_RDAP_COMMON[key]['description'][
                        '_name'] if (hr and show_name) else None,
                    value=description.replace(
                        '\n',
                        '\n{0}'.format(generate_output(line='3'))
                    ),
                    colorize=colorize
                )
                output += self.generate_output_list(
                    source=source,
                    key='links',
                    val=links,
                    line=str(int(line)+1),
                    hr=hr,
                    show_name=show_name,
                    colorize=colorize
                )

                count += 1

        return output

    def generate_output_network(self, json_data=None, hr=True, show_name=False,
                                colorize=True):

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_RDAP['network']['_short'] if hr else 'network',
            name=HR_RDAP['network']['_name'] if (hr and show_name) else None,
            is_parent=True,
            colorize=colorize
        )

        for key, val in json_data['network'].items():

            if key in ['links', 'status']:

                output += self.generate_output_list(
                    source='network',
                    key=key,
                    val=val,
                    line='1',
                    hr=hr,
                    show_name=show_name,
                    colorize=colorize
                )

            elif key in ['notices', 'remarks']:

                output += self.generate_output_notices(
                    source='network',
                    key=key,
                    val=val,
                    line='1',
                    hr=hr,
                    show_name=show_name,
                    colorize=colorize
                )

            elif key == 'events':

                output += self.generate_output_events(
                    source='network',
                    key=key,
                    val=val,
                    line='1',
                    hr=hr,
                    show_name=show_name,
                    colorize=colorize
                )

            elif key not in ['raw']:

                output += generate_output(
                    line='1',
                    short=HR_RDAP['network'][key]['_short'] if hr else key,
                    name=HR_RDAP['network'][key]['_name'] if (
                        hr and show_name) else None,
                    value=val,
                    colorize=colorize
                )

        return output

    def generate_output_objects(self, json_data=None, hr=True, show_name=False,
                                colorize=True):

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_RDAP['objects']['_short'] if hr else 'objects',
            name=HR_RDAP['objects']['_name'] if (hr and show_name) else None,
            is_parent=True,
            colorize=colorize
        )

        count = 0
        for obj_name, obj in json_data['objects'].items():
            if count > 0:
                output += self.generate_output_newline(
                    line='1',
                    colorize=colorize
                )
            count += 1

            output += generate_output(
                line='1',
                short=obj_name,
                is_parent=True,
                colorize=colorize
            )

            for key, val in obj.items():

                if key in ['links', 'entities', 'roles', 'status']:

                    output += self.generate_output_list(
                        source='objects',
                        key=key,
                        val=val,
                        line='2',
                        hr=hr,
                        show_name=show_name,
                        colorize=colorize
                    )

                elif key in ['notices', 'remarks']:

                    output += self.generate_output_notices(
                        source='objects',
                        key=key,
                        val=val,
                        line='2',
                        hr=hr,
                        show_name=show_name,
                        colorize=colorize
                    )

                elif key == 'events':

                    output += self.generate_output_events(
                        source='objects',
                        key=key,
                        val=val,
                        line='2',
                        hr=hr,
                        show_name=show_name,
                        colorize=colorize
                    )

                elif key == 'contact':

                    output += generate_output(
                        line='2',
                        short=HR_RDAP['objects']['contact'][
                            '_short'] if hr else 'contact',
                        name=HR_RDAP['objects']['contact']['_name'] if (
                            hr and show_name) else None,
                        is_parent=False if (val is None or
                                            len(val) == 0) else True,
                        value='None' if (val is None or
                                         len(val) == 0) else None,
                        colorize=colorize
                    )

                    if val is not None:

                        for k, v in val.items():

                            if k in ['phone', 'address', 'email']:

                                output += generate_output(
                                    line='3',
                                    short=HR_RDAP['objects']['contact'][k][
                                        '_short'] if hr else k,
                                    name=HR_RDAP['objects']['contact'][k][
                                        '_name'] if (
                                        hr and show_name) else None,
                                    is_parent=False if (
                                        val is None or
                                        len(val) == 0
                                    ) else True,
                                    value='None' if (val is None or
                                                     len(val) == 0) else None,
                                    colorize=colorize
                                )

                                if v is not None:
                                    for item in v:
                                        i_type = ', '.join(item['type']) if (
                                            isinstance(item['type'], list)
                                        ) else item['type']

                                        i_type = i_type if (
                                            i_type is not None and
                                            len(i_type) > 0) else ''

                                        i_value = item['value'].replace(
                                            '\n',
                                            '\n{0}'.format(
                                                generate_output(
                                                    line='4',
                                                    is_parent=True,
                                                    colorize=colorize
                                                ).replace('\n', ''))
                                        )

                                        tmp_out = '{0}{1}{2}'.format(
                                            i_type,
                                            ': ' if i_type != '' else '',
                                            i_value.encode('utf-8')
                                        )

                                        output += generate_output(
                                            line='4',
                                            value=tmp_out,
                                            colorize=colorize
                                        )

                            else:

                                output += generate_output(
                                    line='3',
                                    short=HR_RDAP['objects']['contact'][k][
                                        '_short'] if hr else k,
                                    name=HR_RDAP['objects']['contact'][k][
                                        '_name'] if (
                                        hr and show_name) else None,
                                    value=v,
                                    colorize=colorize
                                )

                elif key not in ['raw']:

                    output += generate_output(
                        line='2',
                        short=HR_RDAP['objects'][key]['_short'] if hr else key,
                        name=HR_RDAP['objects'][key]['_name'] if (
                            hr and show_name) else None,
                        value=val,
                        colorize=colorize
                    )

        return output

    def lookup_rdap(self, hr=True, show_name=False, colorize=True, **kwargs):

        # Perform the RDAP lookup
        ret = self.obj.lookup_rdap(**kwargs)

        # Header
        output = self.generate_output_header(query_type='RDAP')

        # ASN
        output += self.generate_output_asn(
            json_data=ret, hr=hr, show_name=show_name, colorize=colorize
        )
        output += self.generate_output_newline(colorize=colorize)

        # Entities
        output += self.generate_output_entities(
            json_data=ret, hr=hr, show_name=show_name, colorize=colorize
        )
        output += self.generate_output_newline(colorize=colorize)

        # Network
        output += self.generate_output_network(
            json_data=ret, hr=hr, show_name=show_name, colorize=colorize
        )
        output += self.generate_output_newline(colorize=colorize)

        # Objects
        output += self.generate_output_objects(
            json_data=ret, hr=hr, show_name=show_name, colorize=colorize
        )
        output += self.generate_output_newline(colorize=colorize)

        return output

    def generate_output_whois_nets(self, json_data=None, hr=True,
                                   show_name=False, colorize=True):

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_WHOIS['nets']['_short'] if hr else 'nets',
            name=HR_WHOIS['nets']['_name'] if (hr and show_name) else None,
            is_parent=True,
            colorize=colorize
        )

        count = 0
        for net in json_data['nets']:
            if count > 0:
                output += self.generate_output_newline(
                    line='1',
                    colorize=colorize
                )
            count += 1

            output += generate_output(
                line='1',
                short=net['handle'],
                is_parent=True,
                colorize=colorize
            )

            for key, val in net.items():

                if val and '\n' in val:

                    output += generate_output(
                        line='2',
                        short=HR_WHOIS['nets'][key]['_short'] if hr else key,
                        name=HR_WHOIS['nets'][key]['_name'] if (
                            hr and show_name) else None,
                        is_parent=False if (val is None or
                                            len(val) == 0) else True,
                        value='None' if (val is None or
                                         len(val) == 0) else None,
                        colorize=colorize
                    )

                    for v in val.split('\n'):
                        output += generate_output(
                            line='3',
                            value=v,
                            colorize=colorize
                        )

                else:

                    output += generate_output(
                        line='2',
                        short=HR_WHOIS['nets'][key]['_short'] if hr else key,
                        name=HR_WHOIS['nets'][key]['_name'] if (
                            hr and show_name) else None,
                        value=val,
                        colorize=colorize
                    )

        return output

    def generate_output_whois_referral(self, json_data=None, hr=True,
                                       show_name=False, colorize=True):

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_WHOIS['referral']['_short'] if hr else 'referral',
            name=HR_WHOIS['referral']['_name'] if (hr and show_name) else None,
            is_parent=False if json_data['referral'] is None else True,
            value='None' if json_data['referral'] is None else None,
            colorize=colorize
        )

        if json_data['referral']:

            for key, val in json_data['referral'].items():

                if val and '\n' in val:

                    output += generate_output(
                        line='1',
                        short=HR_WHOIS['nets'][key]['_short'] if hr else key,
                        name=HR_WHOIS['nets'][key]['_name'] if (
                            hr and show_name) else None,
                        is_parent=False if (val is None or
                                            len(val) == 0) else True,
                        value='None' if (val is None or
                                         len(val) == 0) else None,
                        colorize=colorize
                    )

                    for v in val.split('\n'):
                        output += generate_output(
                            line='2',
                            value=v,
                            colorize=colorize
                        )

                else:

                    output += generate_output(
                        line='1',
                        short=HR_WHOIS['nets'][key]['_short'] if hr else key,
                        name=HR_WHOIS['nets'][key]['_name'] if (
                            hr and show_name) else None,
                        value=val,
                        colorize=colorize
                    )

        return output

    def lookup_whois(self, hr=True, show_name=False, colorize=True, **kwargs):

        # Perform the RDAP lookup
        ret = self.obj.lookup_whois(**kwargs)

        # Header
        output = self.generate_output_header(query_type='Legacy Whois')

        # ASN
        output += self.generate_output_asn(
            json_data=ret, hr=hr, show_name=show_name, colorize=colorize
        )
        output += self.generate_output_newline(colorize=colorize)

        # Network
        output += self.generate_output_whois_nets(
            json_data=ret, hr=hr, show_name=show_name, colorize=colorize
        )
        output += self.generate_output_newline(colorize=colorize)

        # Referral
        output += self.generate_output_whois_referral(
            json_data=ret, hr=hr, show_name=show_name, colorize=colorize
        )
        output += self.generate_output_newline(colorize=colorize)

        return output

if args.addr:

    results = IPWhoisCLI(
        args.addr[0],
        args.timeout,
        args.proxy_http[0],
        args.proxy_https[0],
        args.allow_permutations
    )

    if args.whois:

        print(results.lookup_whois(
            hr=args.hr,
            show_name=args.show_name,
            colorize=args.colorize,
            inc_raw=args.inc_raw,
            retry_count=args.retry_count,
            get_referral=args.get_referral,
            extra_blacklist=args.extra_blacklist[0],
            ignore_referral_errors=args.ignore_referral_errors,
            field_list=args.field_list[0],
            asn_alts=args.asn_alts[0]
        ))

    else:

        print(results.lookup_rdap(
            hr=args.hr,
            show_name=args.show_name,
            colorize=args.colorize,
            inc_raw=args.inc_raw,
            retry_count=args.retry_count,
            depth=args.depth,
            excluded_entities=args.excluded_entities[0],
            bootstrap=args.bootstrap,
            rate_limit_timeout=args.rate_limit_timeout,
            asn_alts=args.asn_alts[0]
        ))
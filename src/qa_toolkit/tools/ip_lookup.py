import socket
import datetime
import re

import requests
import ipaddress


class IPQueryTool:
    """改进的IP地址查询工具类 - 使用全球IP数据库API"""

    def __init__(self):
        self.data_source = "全球IP数据库API"
        # 免费的IP查询API服务
        self.ip_apis = {
            'ipapi': 'https://ipapi.co/{ip}/json/',
            'ipapi_com': 'http://ip-api.com/json/{ip}',
            'ipinfo': 'https://ipinfo.io/{ip}/json',
            'ipapi_is': 'https://api.ipapi.com/api/{ip}?access_key=YOUR_API_KEY'  # 需要注册获取免费key
        }

    def _query_ip_api(self, ip_address, api_name):
        """查询IP信息的通用方法"""
        try:
            if api_name == 'ipapi':
                url = self.ip_apis['ipapi'].format(ip=ip_address)
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'country': data.get('country_name', '未知'),
                        'province': data.get('region', '未知'),
                        'city': data.get('city', '未知'),
                        'isp': data.get('org', '未知'),
                        'location': f"{data.get('country_name', '')} {data.get('region', '')} {data.get('city', '')}".strip(),
                        'asn': data.get('asn', ''),
                        'timezone': data.get('timezone', ''),
                        'currency': data.get('currency', ''),
                        'languages': data.get('languages', '')
                    }

            elif api_name == 'ipapi_com':
                url = self.ip_apis['ipapi_com'].format(ip=ip_address)
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        return {
                            'country': data.get('country', '未知'),
                            'province': data.get('regionName', '未知'),
                            'city': data.get('city', '未知'),
                            'isp': data.get('isp', '未知'),
                            'location': f"{data.get('country', '')} {data.get('regionName', '')} {data.get('city', '')}".strip(),
                            'asn': data.get('as', ''),
                            'timezone': data.get('timezone', ''),
                            'org': data.get('org', ''),
                            'zip': data.get('zip', '')
                        }

            elif api_name == 'ipinfo':
                url = self.ip_apis['ipinfo'].format(ip=ip_address)
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    loc = data.get('loc', '').split(',')
                    country = data.get('country', '')
                    return {
                        'country': self._get_country_name(country),
                        'province': data.get('region', '未知'),
                        'city': data.get('city', '未知'),
                        'isp': data.get('org', '未知'),
                        'location': data.get('country', '') + ' ' + data.get('region', '') + ' ' + data.get('city', ''),
                        'asn': data.get('org', '').split(' ')[0] if 'AS' in data.get('org', '') else '',
                        'timezone': data.get('timezone', ''),
                        'coordinates': data.get('loc', '')
                    }

            return None
        except Exception as e:
            print(f"API {api_name} 查询失败: {e}")
            return None

    def _get_country_name(self, country_code):
        """将国家代码转换为国家名称"""
        country_map = {
            'CN': '中国', 'US': '美国', 'JP': '日本', 'KR': '韩国',
            'SG': '新加坡', 'DE': '德国', 'FR': '法国', 'GB': '英国',
            'RU': '俄罗斯', 'IN': '印度', 'BR': '巴西', 'CA': '加拿大',
            'AU': '澳大利亚', 'TW': '中国台湾', 'HK': '中国香港', 'MO': '中国澳门'
        }
        return country_map.get(country_code, country_code)

    def get_detailed_location(self, ip_address):
        """获取详细的IP地理位置信息 - 使用全球API"""
        # 首先检查是否是私有IP
        try:
            ip = ipaddress.ip_address(ip_address)
            if ip.is_private:
                return {
                    'country': '本地网络',
                    'province': '私有IP',
                    'city': '内网地址',
                    'isp': '局域网',
                    'location': '私有网络地址',
                    'ip_type': '私有IP'
                }
        except:
            pass

        # 依次尝试不同的API
        apis_to_try = ['ipapi_com', 'ipapi', 'ipinfo']

        for api_name in apis_to_try:
            result = self._query_ip_api(ip_address, api_name)
            if result and result.get('country') != '未知':
                return result

        # 如果所有API都失败，返回默认值
        return {
            'country': '未知',
            'province': '未知',
            'city': '未知',
            'isp': '未知',
            'location': '未知',
            'ip_type': '公网IP'
        }

    # def get_public_ip(self):
    #     """改进的公网IP获取方法"""
    #     services = [
    #         'https://api.ipify.org',
    #         'https://ident.me',
    #         'https://checkip.amazonaws.com',
    #         'https://ipinfo.io/ip',
    #         'https://api.my-ip.io/ip',
    #         'https://ipecho.net/plain'
    #     ]
    #
    #     for service in services:
    #         try:
    #             response = requests.get(service, timeout=5)
    #             if response.status_code == 200:
    #                 ip = response.text.strip()
    #                 # 验证IP格式
    #                 if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
    #                     return ip
    #         except:
    #             continue
    #
    #     return "获取公网IP失败"

    def get_ip_domain_info(self, target, is_ip):
        """获取IP/域名详细信息"""
        try:
            info_dict = {}

            if is_ip:
                info_dict['IP地址'] = target
                location_info = self.get_detailed_location(target)
                info_dict.update({
                    '国家': location_info.get('country', '未知'),
                    '省份': location_info.get('province', '未知'),
                    '城市': location_info.get('city', '未知'),
                    '运营商': location_info.get('isp', '未知'),
                    '地理位置': location_info.get('location', '未知')
                })
                info_dict['IP类型'] = self._get_ip_type(target)
            else:
                info_dict['域名'] = target
                try:
                    # 获取所有A记录
                    ip_addresses = []
                    try:
                        # 获取IPv4地址
                        ipv4 = socket.gethostbyname(target)
                        ip_addresses.append(ipv4)
                    except:
                        pass

                    # 尝试获取更多IP地址
                    try:
                        addrinfo = socket.getaddrinfo(target, None)
                        for addr in addrinfo:
                            ip = addr[4][0]
                            if ip not in ip_addresses:
                                ip_addresses.append(ip)
                    except:
                        pass

                    if ip_addresses:
                        primary_ip = ip_addresses[0]
                        info_dict['解析IP'] = primary_ip
                        if len(ip_addresses) > 1:
                            info_dict['所有IP'] = ', '.join(ip_addresses)

                        location_info = self.get_detailed_location(primary_ip)
                        info_dict.update({
                            '国家': location_info.get('country', '未知'),
                            '省份': location_info.get('province', '未知'),
                            '城市': location_info.get('city', '未知'),
                            '运营商': location_info.get('isp', '未知'),
                            '地理位置': location_info.get('location', '未知')
                        })
                    else:
                        info_dict['解析IP'] = '解析失败'
                        info_dict.update(self._default_location())
                except Exception as e:
                    info_dict['解析IP'] = f'解析失败: {str(e)}'
                    info_dict.update(self._default_location())
                info_dict['类型'] = '域名'

            # 添加其他信息
            info_dict['ASN信息'] = self.get_asn_info(target)
            info_dict['网络段'] = self._get_network_segment(target)
            info_dict['查询时间'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            info_dict['数据来源'] = self.data_source

            return {
                'success': True,
                'data': info_dict
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _get_ip_type(self, ip_address):
        """获取IP类型"""
        try:
            ip = ipaddress.ip_address(ip_address)
            if ip.is_private:
                return '私有IP'
            elif ip.is_global:
                return '公网IPv4' if ip.version == 4 else '公网IPv6'
            elif ip.is_multicast:
                return '组播IP'
            elif ip.is_link_local:
                return '链路本地IP'
            else:
                return 'IPv4' if '.' in ip_address else 'IPv6'
        except:
            return 'IPv4' if '.' in ip_address else 'IPv6'

    def _get_network_segment(self, target):
        """获取网络段信息"""
        try:
            if '.' in target and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target):
                ip_parts = target.split('.')
                return f'{ip_parts[0]}.{ip_parts[1]}.0.0/16'
            return '未知'
        except:
            return '未知'

    def get_asn_info(self, target):
        """获取ASN信息"""
        try:
            if '.' in target and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target):
                # 对于IP地址，使用API获取ASN信息
                location_info = self.get_detailed_location(target)
                asn = location_info.get('asn', '')
                isp = location_info.get('isp', '')

                if asn:
                    return f'{asn} ({isp})' if isp else asn
                elif isp:
                    return isp

                # 回退到本地映射
                return self._get_asn_from_local(target)
            else:
                # 对于域名，使用本地映射
                return self._get_asn_from_domain(target)

        except Exception as e:
            return f'AS未知 (错误: {str(e)})'

    def _get_asn_from_local(self, ip_address):
        """从本地映射获取ASN信息"""
        ip_parts = ip_address.split('.')
        ip_prefix = f"{ip_parts[0]}.{ip_parts[1]}"

        asn_mapping = {
            '8.8': 'AS15169 (Google LLC)',
            '1.1': 'AS13335 (Cloudflare, Inc.)',
            '9.9': 'AS19281 (Quad9)',
            '64.6': 'AS36692 (OpenDNS)',
            '208.67': 'AS36692 (OpenDNS)',
            '192.168': 'AS0 (私有网络)',
            '10.0': 'AS0 (私有网络)',
            '172.16': 'AS0 (私有网络)',
            '169.254': 'AS0 (链路本地)'
        }

        return asn_mapping.get(ip_prefix, 'AS未知')

    def _get_asn_from_domain(self, domain):
        """从域名获取ASN信息"""
        domain_lower = domain.lower()

        asn_mapping = {
            'google': 'AS15169 (Google LLC)',
            'cloudflare': 'AS13335 (Cloudflare, Inc.)',
            'baidu': 'AS55990 (Baidu)',
            'aliyun': 'AS45102 (Alibaba Cloud)',
            'alibaba': 'AS45102 (Alibaba Cloud)',
            'tencent': 'AS45090 (Tencent Cloud)',
            'qq.com': 'AS45090 (Tencent Cloud)',
            'huawei': 'AS55990 (Huawei Cloud)',
            'amazon': 'AS16509 (Amazon.com, Inc.)',
            'aws': 'AS16509 (Amazon.com, Inc.)',
            'microsoft': 'AS8075 (Microsoft Corporation)',
            'azure': 'AS8075 (Microsoft Corporation)',
            'facebook': 'AS32934 (Facebook)',
            'twitter': 'AS13414 (Twitter)',
            'apple': 'AS714 (Apple Inc.)'
        }

        for key, value in asn_mapping.items():
            if key in domain_lower:
                return value

        return 'AS未知'

    def _default_location(self):
        """默认地理位置信息"""
        return {
            '国家': '未知',
            '省份': '未知',
            '城市': '未知',
            '运营商': '未知',
            '地理位置': '未知'
        }

    # 保留其他原有方法...
    def get_rdns_info(self, ip_address):
        """获取rDNS信息"""
        try:
            hostname = socket.gethostbyaddr(ip_address)[0]
            return {
                'success': True,
                'data': {'rDNS': hostname}
            }
        except:
            return {
                'success': False,
                'error': '无法获取rDNS信息'
            }

    def convert_ip_address(self, input_value, conversion_type):
        """IP地址格式转换"""
        try:
            result = {}

            if conversion_type == "十进制 ↔ 点分十进制":
                if '.' in input_value:  # 点分十进制转十进制
                    parts = input_value.split('.')
                    if len(parts) == 4:
                        decimal = (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
                        result['点分十进制'] = input_value
                        result['十进制'] = str(decimal)
                else:  # 十进制转点分十进制
                    decimal = int(input_value)
                    ip = f"{(decimal >> 24) & 0xFF}.{(decimal >> 16) & 0xFF}.{(decimal >> 8) & 0xFF}.{decimal & 0xFF}"
                    result['十进制'] = input_value
                    result['点分十进制'] = ip

            elif conversion_type == "点分十进制 ↔ 十六进制":
                if '.' in input_value:  # 点分十进制转十六进制
                    parts = input_value.split('.')
                    if len(parts) == 4:
                        hex_value = '0x' + ''.join(f'{int(part):02x}' for part in parts)
                        result['点分十进制'] = input_value
                        result['十六进制'] = hex_value
                else:  # 十六进制转点分十进制
                    hex_value = input_value.replace('0x', '')
                    if len(hex_value) == 8:
                        ip = '.'.join(str(int(hex_value[i:i + 2], 16)) for i in range(0, 8, 2))
                        result['十六进制'] = input_value
                        result['点分十进制'] = ip

            else:  # 点分十进制 ↔ 二进制
                if '.' in input_value:  # 点分十进制转二进制
                    parts = input_value.split('.')
                    if len(parts) == 4:
                        binary = '.'.join(f'{int(part):08b}' for part in parts)
                        result['点分十进制'] = input_value
                        result['二进制'] = binary
                else:  # 二进制转点分十进制
                    binary_parts = input_value.split('.')
                    if len(binary_parts) == 4:
                        ip = '.'.join(str(int(part, 2)) for part in binary_parts)
                        result['二进制'] = input_value
                        result['点分十进制'] = ip

            return {'success': True, 'data': result}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def set_data_source(self, source):
        """设置数据来源"""
        self.data_source = source

    def get_tool_info(self):
        """获取工具信息"""
        return {
            'name': '改进的IP地址查询工具',
            'version': '2.0',
            'author': 'IP Query Tool',
            'functions': [
                'IP/域名信息查询（全球数据库）',
                'ASN信息查询',
                'rDNS查询',
                'IP反查网站',
                'IP地址格式转换'
            ]
        }


    def _get_service_name(self, port):
        """获取端口对应的服务名称"""
        common_ports = {
            21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
            80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS',
            993: 'IMAPS', 995: 'POP3S', 3306: 'MySQL', 3389: 'RDP',
            5432: 'PostgreSQL', 6379: 'Redis', 27017: 'MongoDB'
        }
        return common_ports.get(port, '未知')







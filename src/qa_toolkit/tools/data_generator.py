import ast
import datetime
import json
import random
from typing import Any, Dict, List, Optional, Union
import streamlit as st

from qa_toolkit.config.constants import PROVINCE_CITY_AREA_CODES, LOWERCASE, UPPERCASE, PROVINCE_MAP, COUNTRY_FORMATS, \
    MOBILE_PREFIXES, UNICON_PREFIXES, TELECON_PREFIXES, BROADCAST_PREFIXES, OPERATOR_PREFIXES, PASSWORD_OPTIONS


COMMON_LAST_NAMES = ["王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴"]
COMMON_FIRST_NAMES = ["晨", "浩", "妍", "磊", "静", "博", "婷", "宇", "欣", "凯", "蕾", "然"]
COMMON_DEPARTMENTS = ["测试", "研发", "产品", "运营", "客服", "财务", "行政"]
COMMON_ROLES = ["测试工程师", "开发工程师", "产品经理", "运营专员", "数据分析师", "实施顾问"]
REGISTER_SOURCES = ["Web", "iOS", "Android", "小程序", "OpenAPI"]
ADDRESS_LABELS = ["家庭", "公司", "学校", "临时地址"]
PAY_STATUSES = ["待支付", "支付成功", "退款中", "已退款"]
COMMON_PRODUCTS = ["会员服务", "企业套餐", "测试账号包", "数据看板", "自动化插件", "短信包"]


class DataGenerator:
    """数据生成器类，封装了多种数据生成功能"""

    def __init__(self, locale='zh_CN'):
        """初始化数据生成器

        Args:
            locale: 地区设置，默认为中文
        """
        self.locale = locale
        self.faker_available = False
        self.fake = None

        # 尝试导入Faker
        try:
            from faker import Faker
            self.fake = Faker(locale)
            self.faker_available = True
        except ImportError:
            self.faker_available = False
            print("Faker库未安装，部分高级功能将受限。请运行: pip install faker")

    def _build_fake(self, seed: Optional[int] = None):
        """按需创建可选的、可复现的 Faker 实例。"""
        if not self.faker_available:
            return None

        from faker import Faker

        fake = Faker(self.locale)
        if seed is not None:
            fake.seed_instance(seed)
        return fake

    def _get_random_context(self, seed: Optional[int] = None):
        """构造一组随机上下文，便于生成可复现的数据。"""
        rng = random.Random(seed) if seed is not None else random.Random()
        base_now = (
            datetime.datetime(2024, 1, 1, 9, 0, 0)
            if seed is not None else
            datetime.datetime.now().replace(microsecond=0)
        )
        fake = self._build_fake(seed)
        return rng, fake, base_now

    def _normalize_batch_tag(self, batch_tag: str, default: str = "qa") -> str:
        """标准化批次标识，便于拼接唯一字段。"""
        raw = "".join(ch for ch in str(batch_tag or "") if ch.isalnum())
        return (raw or default).lower()

    def _choose_region(self, rng) -> Dict[str, str]:
        """随机选择一个省市区号组合。"""
        province = rng.choice(list(PROVINCE_CITY_AREA_CODES.keys()))
        cities = list(PROVINCE_CITY_AREA_CODES.get(province, {}).keys())
        city = rng.choice(cities) if cities else province
        area_code = PROVINCE_CITY_AREA_CODES.get(province, {}).get(city, "")
        return {"province": province, "city": city, "area_code": area_code}

    def _generate_name(self, rng, fake=None, gender: str = "随机") -> str:
        """生成姓名，优先使用 Faker。"""
        if fake:
            if gender == "男" and hasattr(fake, "name_male"):
                return fake.name_male()
            if gender == "女" and hasattr(fake, "name_female"):
                return fake.name_female()
            return fake.name()

        return f"{rng.choice(COMMON_LAST_NAMES)}{rng.choice(COMMON_FIRST_NAMES)}{rng.choice(COMMON_FIRST_NAMES)}"

    def _generate_company_name(self, rng, fake=None) -> str:
        if fake:
            return fake.company()
        return f"{rng.choice(['星云', '数科', '云峰', '拓维', '极客', '启航'])}{rng.choice(['科技', '信息', '软件', '网络'])}有限公司"

    def _generate_job_title(self, rng, fake=None) -> str:
        if fake:
            return fake.job()
        return rng.choice(COMMON_ROLES)

    def _generate_datetime_string(self, rng, base_now: datetime.datetime, max_days_back: int = 30) -> str:
        """生成最近一段时间内的时间字符串。"""
        day_offset = rng.randint(0, max_days_back)
        minute_offset = rng.randint(0, 24 * 60 - 1)
        value = base_now - datetime.timedelta(days=day_offset, minutes=minute_offset)
        return value.strftime("%Y-%m-%d %H:%M:%S")

    def _mutate_check_code(self, id_card: str) -> str:
        """篡改身份证校验位，生成异常值。"""
        if not id_card:
            return id_card
        wrong_code = "0" if id_card[-1] != "0" else "1"
        return id_card[:-1] + wrong_code

    def get_test_data_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """返回适用于测试/研发的结构化造数场景。"""
        return {
            "注册登录账号": {
                "description": "适合注册、登录、找回密码、账号绑定和用户中心场景。",
                "fields": ["username", "password", "phone", "email", "real_name", "id_card", "register_source"]
            },
            "企业员工档案": {
                "description": "适合后台导入员工、组织架构、审批流和通讯录场景。",
                "fields": ["employee_no", "name", "department", "role", "phone", "email", "hire_date", "status"]
            },
            "收货地址簿": {
                "description": "适合电商、物流、地址簿管理和联系人信息场景。",
                "fields": ["receiver_name", "receiver_phone", "province", "city", "address", "postcode", "label"]
            },
            "订单支付记录": {
                "description": "适合订单流、支付回调、账单对账和数据联调场景。",
                "fields": ["order_no", "user_no", "product_name", "order_amount", "discount_amount", "pay_status", "order_status"]
            }
        }

    def get_boundary_field_templates(self) -> Dict[str, Dict[str, str]]:
        """返回常用字段的边界值/异常值说明。"""
        return {
            "用户名": {
                "description": "默认规则：只允许字母、数字、下划线，长度受 min/max 约束。"
            },
            "密码": {
                "description": "默认规则：需包含大小写字母、数字和特殊字符。"
            },
            "邮箱": {
                "description": "默认规则：遵循常见邮箱格式校验。"
            },
            "手机号": {
                "description": "默认规则：中国大陆 11 位手机号。"
            },
            "身份证号": {
                "description": "默认规则：中国大陆 18 位身份证号，需满足校验位。"
            },
            "金额": {
                "description": "默认规则：数值需在范围内，最多保留两位小数。"
            }
        }

    def safe_generate(self, generator_func, *args, **kwargs):
        """安全执行生成函数"""
        try:
            return generator_func(*args, **kwargs)
        except Exception as e:
            st.error(f"生成过程中发生错误：{e}")
            return None

    def _safe_parse_profile_dict(self, profile_dict: Union[Dict, str]) -> Dict[str, Any]:
        """将个人信息输入安全解析为字典，拒绝执行任意代码。"""
        if isinstance(profile_dict, dict):
            return profile_dict

        raw = str(profile_dict or "").strip()
        if not raw:
            raise ValueError("个人信息为空。")

        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = ast.literal_eval(raw)

        if not isinstance(parsed, dict):
            raise ValueError("个人信息格式无效，应为字典结构。")
        return parsed

    def format_profile_data(self, profile_dict: Union[Dict, str]) -> str:
        """格式化完整个人信息显示

        Args:
            profile_dict: 个人信息字典或字符串

        Returns:
            格式化后的个人信息字符串
        """
        try:
            profile_dict = self._safe_parse_profile_dict(profile_dict)

            # 提取基本信息
            name = profile_dict.get('name', '未知')
            sex = '女' if profile_dict.get('sex') == 'F' else '男'
            birthdate = profile_dict.get('birthdate', '未知')
            mail = profile_dict.get('mail', '（信息缺失）')
            job = profile_dict.get('job', '（信息缺失）')
            address = profile_dict.get('address', '（信息缺失）')
            company = profile_dict.get('company', '（信息缺失）')
            website = profile_dict.get('website', [])
            username = profile_dict.get('username', '（信息缺失）')

            # 格式化出生日期
            if birthdate != '未知':
                if hasattr(birthdate, 'year'):
                    birthdate = f"{birthdate.year}年{birthdate.month}月{birthdate.day}日"
                else:
                    birthdate = str(birthdate)

            # 格式化地址（简化显示）
            if address != '（信息缺失）':
                address_parts = str(address).split(' ')
                if len(address_parts) > 0:
                    simplified_address = address_parts[0]
                    if '省' in simplified_address:
                        parts = simplified_address.split('省')
                        if len(parts) > 1:
                            city_part = parts[1]
                            if '市' in city_part:
                                city_parts = city_part.split('市')
                                simplified_address = parts[0] + '省' + city_parts[0] + '市'
                    elif '自治区' in simplified_address:
                        parts = simplified_address.split('自治区')
                        if len(parts) > 1:
                            city_part = parts[1]
                            if '市' in city_part:
                                city_parts = city_part.split('市')
                                simplified_address = parts[0] + '自治区' + city_parts[0] + '市'
                    elif '市' in simplified_address:
                        parts = simplified_address.split('市')
                        if len(parts) > 1:
                            simplified_address = parts[0] + '市'
                    address = simplified_address

            # 构建格式化结果
            result = []
            result.append("------------------------------")
            result.append(f"个人信息--{name}")
            result.append(f"姓名： {name}")
            result.append(f"性别： {sex}")
            result.append(f"出生日期： {birthdate}")
            result.append(f"电子邮箱： {mail}")
            result.append("联系电话： （信息缺失）")
            result.append(f"求职意向： {job}")
            result.append(f"所在地区： {address}")
            result.append("")
            result.append("工作经历")
            result.append(f"公司： {company}")
            result.append(f"职位： {job}")
            result.append("其他信息")

            if website:
                website_str = "， ".join(website)
                result.append(f"个人网站/主页： {website_str}")
            else:
                result.append("个人网站/主页： （信息缺失）")

            result.append(f"用户名： {username}")
            result.append("------------------------------")

            return "\n".join(result)

        except Exception as e:
            return f"格式化数据时出错: {str(e)}\n原始数据: {profile_dict}"

    def generate_faker_data(self, category: str, subcategory: str, count: int = 1, **kwargs) -> List[str]:
        """使用Faker生成数据

        Args:
            category: 数据类别（如：人物信息、地址信息等）
            subcategory: 数据子类别（如：随机姓名、随机地址等）
            count: 生成数量
            **kwargs: 其他参数

        Returns:
            生成的数据列表
        """
        if not self.faker_available:
            return ["Faker库未安装，部分高级功能受限。请运行: pip install faker"]

        results = []
        try:
            for i in range(count):
                if category == "人物信息":
                    if subcategory == "随机姓名":
                        results.append(self.fake.name())
                    elif subcategory == "随机姓":
                        results.append(self.fake.last_name())
                    elif subcategory == "随机名":
                        results.append(self.fake.first_name())
                    elif subcategory == "男性姓名":
                        results.append(self.fake.name_male())
                    elif subcategory == "女性姓名":
                        results.append(self.fake.name_female())
                    elif subcategory == "完整个人信息":
                        raw_profile = self.fake.profile()
                        formatted_profile = self.format_profile_data(raw_profile)
                        results.append(formatted_profile)

                elif category == "地址信息":
                    if subcategory == "随机地址":
                        results.append(self.fake.address())
                    elif subcategory == "随机城市":
                        results.append(self.fake.city())
                    elif subcategory == "随机国家":
                        results.append(self.fake.country())
                    elif subcategory == "随机邮编":
                        results.append(self.fake.postcode())
                    elif subcategory == "随机街道":
                        results.append(self.fake.street_address())

                elif category == "网络信息":
                    if subcategory == "随机邮箱":
                        results.append(self.fake.email())
                    elif subcategory == "安全邮箱":
                        results.append(self.fake.safe_email())
                    elif subcategory == "公司邮箱":
                        results.append(self.fake.company_email())
                    elif subcategory == "免费邮箱":
                        results.append(self.fake.free_email())
                    elif subcategory == "随机域名":
                        results.append(self.fake.domain_name())
                    elif subcategory == "随机URL":
                        results.append(self.fake.url())
                    elif subcategory == "随机IP地址":
                        results.append(self.fake.ipv4())
                    elif subcategory == "随机用户代理":
                        results.append(self.fake.user_agent())

                elif category == "公司信息":
                    if subcategory == "随机公司名":
                        results.append(self.fake.company())
                    elif subcategory == "公司后缀":
                        results.append(self.fake.company_suffix())
                    elif subcategory == "职位":
                        results.append(self.fake.job())

                elif category == "金融信息":
                    if subcategory == "信用卡号":
                        results.append(self.fake.credit_card_number())
                    elif subcategory == "信用卡提供商":
                        results.append(self.fake.credit_card_provider())
                    elif subcategory == "信用卡有效期":
                        results.append(self.fake.credit_card_expire())
                    elif subcategory == "货币":
                        results.append(self.fake.currency())

                elif category == "日期时间":
                    if subcategory == "随机日期时间":
                        results.append(str(self.fake.date_time()))
                    elif subcategory == "随机日期":
                        results.append(self.fake.date())
                    elif subcategory == "随机时间":
                        results.append(self.fake.time())
                    elif subcategory == "今年日期":
                        results.append(str(self.fake.date_time_this_year()))
                    elif subcategory == "本月日期":
                        results.append(str(self.fake.date_time_this_month()))

                elif category == "文本内容":
                    if subcategory == "随机单词":
                        results.append(self.fake.word())
                    elif subcategory == "随机句子":
                        results.append(self.fake.sentence())
                    elif subcategory == "随机段落":
                        results.append(self.fake.paragraph())
                    elif subcategory == "随机文本":
                        results.append(self.fake.text(max_nb_chars=kwargs.get('length', 200)))

                elif category == "电话号码":
                    if subcategory == "随机手机号":
                        results.append(self.fake.phone_number())
                    elif subcategory == "号段前缀":
                        results.append(self.fake.phonenumber_prefix())

                elif category == "其他信息":
                    if subcategory == "随机颜色":
                        results.append(self.fake.color_name())
                    elif subcategory == "随机UUID":
                        results.append(self.fake.uuid4())
                    elif subcategory == "随机MD5":
                        results.append(self.fake.md5())
                    elif subcategory == "随机SHA1":
                        results.append(self.fake.sha1())
                    elif subcategory == "随机文件扩展名":
                        results.append(self.fake.file_extension())
                    elif subcategory == "随机MIME类型":
                        results.append(self.fake.mime_type())

        except Exception as e:
            results = [f"生成数据时出错: {str(e)}"]

        return results

    def generate_random_string(self, length: int, chars_type: List[str], rng=None) -> str:
        """生成随机字符串

        Args:
            length: 字符串长度
            chars_type: 字符类型列表

        Returns:
            随机字符串
        """
        rng = rng or random
        chars = ""
        if "小写字母" in chars_type:
            chars += LOWERCASE
        if "大写字母" in chars_type:
            chars += UPPERCASE
        if "数字" in chars_type:
            chars += "0123456789"
        if "特殊字符" in chars_type:
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not chars:
            chars = LOWERCASE
        return ''.join(rng.choice(chars) for _ in range(length))

    def generate_random_password(self, length: int, options: List[str], rng=None) -> str:
        """生成随机密码

        Args:
            length: 密码长度
            options: 密码选项

        Returns:
            随机密码
        """
        if self.faker_available and rng is None:
            return self.fake.password(
                length=length,
                special_chars="包含特殊字符" in options,
                digits="包含数字" in options,
                upper_case="包含大写字母" in options,
                lower_case="包含小写字母" in options
            )

        # 备用方案
        rng = rng or random
        password = ""
        chars = ""
        if "包含小写字母" in options:
            password += rng.choice(LOWERCASE)
            chars += LOWERCASE
        if "包含大写字母" in options:
            password += rng.choice(UPPERCASE)
            chars += UPPERCASE
        if "包含数字" in options:
            password += rng.choice("0123456789")
            chars += "0123456789"
        if "包含特殊字符" in options:
            password += rng.choice("!@#$%^&*()_+-=[]{}|;:,.<>?")
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not chars:
            password += rng.choice(LOWERCASE)
            chars += "abcdefghijklmnopqrstuvwxyz0123456789"
            password += rng.choice("0123456789")

        password += ''.join(rng.choice(chars) for _ in range(length - len(password)))
        password_list = list(password)
        rng.shuffle(password_list)
        return ''.join(password_list)

    def generate_random_phone_number(self, operator: str, rng=None) -> str:
        """生成随机电话号码"""
        rng = rng or random
        if self.faker_available and rng is None:
            return self.fake.phone_number()

        if operator == "移动":
            prefix = rng.choice(MOBILE_PREFIXES)
        elif operator == "联通":
            prefix = rng.choice(UNICON_PREFIXES)
        elif operator == "电信":
            prefix = rng.choice(TELECON_PREFIXES)
        elif operator == "广电":
            prefix = rng.choice(BROADCAST_PREFIXES)
        else:
            rand_val = rng.random()
            if rand_val < 0.35:
                prefix = rng.choice(MOBILE_PREFIXES)
            elif rand_val < 0.6:
                prefix = rng.choice(UNICON_PREFIXES)
            elif rand_val < 0.85:
                prefix = rng.choice(TELECON_PREFIXES)
            else:
                prefix = rng.choice(BROADCAST_PREFIXES)

        suffix = ''.join([str(rng.randint(0, 9)) for _ in range(8)])
        return f"{prefix}{suffix}"

    def generate_random_address(self, province: str, city: str, detailed: bool = True, rng=None) -> str:
        """生成随机地址"""
        rng = rng or random
        if not detailed:
            return f"{province}{city}"

        # 详细地址生成
        streets = ["中山路", "解放路", "人民路", "建设路", "和平路", "新华路", "文化路", "胜利路", "团结路", "友谊路"]
        communities = ["小区", "花园", "大厦", "公寓", "广场", "苑", "居", "湾", "城", "国际"]
        numbers = [str(i) for i in range(1, 201)]

        street = rng.choice(streets)
        community = rng.choice(communities)
        number = rng.choice(numbers)

        return f"{province}{city}{street}{number}号{community}{rng.randint(1, 20)}栋{rng.randint(1, 30)}单元{rng.randint(101, 1500)}室"

    def generate_random_id_card(self, province: str, gender: str, min_age: int, max_age: int, rng=None,
                                reference_date: Optional[datetime.datetime] = None) -> str:
        """生成随机身份证号码"""
        rng = rng or random
        reference_date = reference_date or datetime.datetime.now()

        # 1. 生成前6位地区码
        province_code = PROVINCE_MAP.get(province, "11")  # 默认北京
        area_code = province_code + ''.join([str(rng.randint(0, 9)) for _ in range(4)])

        # 2. 生成出生日期码
        current_year = reference_date.year
        birth_year = rng.randint(current_year - max_age, current_year - min_age)
        birth_month = rng.randint(1, 12)

        # 处理不同月份的天数
        if birth_month in [1, 3, 5, 7, 8, 10, 12]:
            max_day = 31
        elif birth_month in [4, 6, 9, 11]:
            max_day = 30
        else:  # 2月
            if (birth_year % 4 == 0 and birth_year % 100 != 0) or (birth_year % 400 == 0):
                max_day = 29
            else:
                max_day = 28

        birth_day = rng.randint(1, max_day)
        birth_date = f"{birth_year:04d}{birth_month:02d}{birth_day:02d}"

        # 3. 生成顺序码
        if gender == "男":
            sequence = rng.randint(1, 499) * 2 + 1
        elif gender == "女":
            sequence = rng.randint(0, 499) * 2
        else:  # 随机
            sequence = rng.randint(0, 999)
        sequence_code = f"{sequence:03d}"

        # 4. 生成前17位
        first_17 = area_code + birth_date + sequence_code

        # 5. 计算校验码
        factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

        total = sum(int(first_17[i]) * factors[i] for i in range(17))
        check_code = check_codes[total % 11]

        # 6. 生成完整身份证号
        return first_17 + check_code

    def generate_conditional_phone(self, operator: str, rng=None) -> str:
        """生成手机号码（仅匹配运营商号段）"""
        rng = rng or random

        # 如果选择"随机"，则从所有运营商中随机选择
        if operator == "随机":
            all_prefixes = []
            for op in OPERATOR_PREFIXES.values():
                all_prefixes.extend(op)
            prefix = rng.choice(all_prefixes)
        else:
            prefix = rng.choice(OPERATOR_PREFIXES[operator])

        # 生成后8位数字（总长度=11位）
        suffix = ''.join([str(rng.randint(0, 9)) for _ in range(11 - len(prefix))])
        return f"{prefix}{suffix}"

    def generate_landline_number(self, operator: str = None, area_code: str = None, rng=None) -> str:
        """生成座机号码（区号可选）"""
        rng = rng or random
        # 1. 区号生成逻辑
        if not area_code:
            # 从完整的省份城市映射中随机选择一个区号
            all_area_codes = []
            for province, cities in PROVINCE_CITY_AREA_CODES.items():
                for city, code in cities.items():
                    all_area_codes.append(code)

            # 去重并确保有可用的区号
            if all_area_codes:
                area_code = rng.choice(all_area_codes)
            else:
                # 备用区号列表
                backup_area_codes = [
                    '010', '021', '022', '023', '020', '024',  # 三位区号
                    '025', '027', '028', '029',  # 省会城市
                    '0512', '0516', '0571', '0574', '0755', '0757'  # 其他常见城市
                ]
                area_code = rng.choice(backup_area_codes)

        # 确保区号格式正确（去掉可能的前导0，然后重新加上）
        area_code = str(int(area_code)).zfill(len(area_code))

        # 2. 根据区号确定本地号码位数
        # 三位区号的城市通常是8位本地号码，其他通常是7位
        if len(area_code) == 3 and area_code in ['010', '021', '022', '023', '020', '024', '025', '027', '028', '029']:
            local_length = 8
        else:
            local_length = 7

        # 3. 生成本地号码（符合运营商规则）
        # 第一位：2-9（不能是0或1）
        first_digit = rng.randint(2, 9)

        # 剩余位数
        if local_length == 8:
            # 8位号码格式：PQR + ABCD 或 PQ + ABCDE
            remaining_length = 7
            remaining = str(rng.randint(0, 10 ** remaining_length - 1)).zfill(remaining_length)
            local_number = str(first_digit) + remaining
        else:
            # 7位号码格式：P + ABCDEF
            remaining_length = 6
            remaining = str(rng.randint(0, 10 ** remaining_length - 1)).zfill(remaining_length)
            local_number = str(first_digit) + remaining

        # 4. 格式化输出
        return f"0{area_code}-{local_number}" if not area_code.startswith('0') else f"{area_code}-{local_number}"

    def generate_international_phone(self, country: str, rng=None) -> str:
        """生成国际手机号码"""
        rng = rng or random
        if country not in COUNTRY_FORMATS:
            # 默认格式
            country_info = {"code": "+1", "format": ["###-###-####"]}
        else:
            country_info = COUNTRY_FORMATS[country]

        # 选择一种格式
        format_pattern = rng.choice(country_info["format"])

        # 生成号码
        phone_number = ""
        for char in format_pattern:
            if char == "#":
                phone_number += str(rng.randint(0, 9))
            else:
                phone_number += char

        return f"{country_info['code']} {phone_number}"

    def generate_conditional_address(self, province: str = None, selected_city: str = None,
                                     detailed: bool = True) -> str:
        """根据条件生成地址"""
        if self.faker_available:
            # Faker生成地址
            if detailed:
                address = self.fake.address()
            else:
                # 不生成详细地址，只到城市级别
                address = f"{self.fake.province()} {self.fake.city()}"
        else:
            # 备用方案
            if province == "随机":
                provinces = ["北京市", "上海市", "广州市", "深圳市", "杭州市", "成都市", "武汉市", "南京市", "西安市"]
                province = random.choice(provinces)
                selected_city = province  # 直辖市城市名与省份相同

            if detailed:
                streets = ["中山路", "解放路", "人民路", "建设路", "和平路", "新华路", "文化路", "胜利路", "团结路", "友谊路"]
                communities = ["小区", "花园", "大厦", "公寓", "广场", "苑", "居", "湾", "城", "国际"]
                numbers = [str(i) for i in range(1, 201)]
                street = random.choice(streets)
                community = random.choice(communities)
                number = random.choice(numbers)
                address = f"{province}{selected_city}{street}{number}号{random.randint(1, 20)}栋{random.randint(1, 30)}单元{random.randint(101, 1500)}室"
            else:
                address = f"{province}{selected_city}"

        return address

    def generate_conditional_id_card(self, province: str = None, gender: str = None, min_age: int = 18,
                                     max_age: int = 60) -> str:
        """根据条件生成身份证号码"""
        if self.faker_available:
            # Faker生成身份证
            id_card = self.fake.ssn()

            if province and province != "随机" and province in PROVINCE_MAP:
                province_code = PROVINCE_MAP[province]
                # 如果生成的身份证前两位不匹配指定省份，重新生成
                if not id_card.startswith(province_code):
                    return self.generate_random_id_card(province, gender or "随机", min_age, max_age)

            return id_card
        else:
            # 备用方案
            return self.generate_random_id_card(
                province if province != "随机" else "北京市",
                gender or "随机",
                min_age,
                max_age
            )

    def generate_random_email(self, domain_option: str, custom_domain: str, selected_domains: List[str], rng=None) -> str:
        """生成随机邮箱"""
        rng = rng or random
        username_length = rng.randint(5, 12)
        username = ''.join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(username_length))

        if domain_option == "自定义域名":
            domain = custom_domain
        else:
            domain = rng.choice(selected_domains) if selected_domains else rng.choice(["gmail.com", "yahoo.com"])

        return f"{username}@{domain}"

    def generate_test_dataset(self, scenario: str, count: int = 10, seed: Optional[int] = None,
                              batch_tag: str = "", email_domain: str = "example.com") -> List[Dict[str, Any]]:
        """按业务场景生成结构化测试数据。"""
        batch_token = self._normalize_batch_tag(batch_tag)
        rng, fake, base_now = self._get_random_context(seed)

        builders = {
            "注册登录账号": self._build_registration_record,
            "企业员工档案": self._build_employee_record,
            "收货地址簿": self._build_shipping_record,
            "订单支付记录": self._build_order_record,
        }

        if scenario not in builders:
            raise ValueError(f"暂不支持的造数场景: {scenario}")

        builder = builders[scenario]
        return [
            builder(
                index=i,
                rng=rng,
                fake=fake,
                base_now=base_now,
                batch_token=batch_token,
                email_domain=email_domain,
            )
            for i in range(1, count + 1)
        ]

    def _build_registration_record(self, index: int, rng, fake, base_now: datetime.datetime, batch_token: str,
                                   email_domain: str) -> Dict[str, Any]:
        region = self._choose_region(rng)
        gender = rng.choice(["男", "女"])
        username = f"{batch_token}_user_{index:03d}_{rng.randint(10, 99)}"
        return {
            "scenario": "注册登录账号",
            "batch_tag": batch_token,
            "username": username,
            "password": self.generate_random_password(12, PASSWORD_OPTIONS, rng=rng),
            "nickname": f"{self._generate_name(rng, fake, gender)}{rng.randint(1, 99)}",
            "real_name": self._generate_name(rng, fake, gender),
            "gender": gender,
            "phone": self.generate_conditional_phone("随机", rng=rng),
            "email": f"{username}@{email_domain}",
            "id_card": self.generate_random_id_card(region["province"], gender, 18, 45, rng=rng, reference_date=base_now),
            "province": region["province"],
            "city": region["city"],
            "address": self.generate_random_address(region["province"], region["city"], detailed=True, rng=rng),
            "register_source": rng.choice(REGISTER_SOURCES),
            "created_at": self._generate_datetime_string(rng, base_now, max_days_back=60),
        }

    def _build_employee_record(self, index: int, rng, fake, base_now: datetime.datetime, batch_token: str,
                               email_domain: str) -> Dict[str, Any]:
        region = self._choose_region(rng)
        gender = rng.choice(["男", "女"])
        department = rng.choice(COMMON_DEPARTMENTS)
        name = self._generate_name(rng, fake, gender)
        employee_no = f"EMP-{batch_token.upper()}-{base_now.strftime('%m%d')}-{index:03d}"
        return {
            "scenario": "企业员工档案",
            "batch_tag": batch_token,
            "employee_no": employee_no,
            "name": name,
            "gender": gender,
            "department": department,
            "role": self._generate_job_title(rng, fake),
            "status": rng.choice(["在职", "试用期", "待入职", "离职归档"]),
            "phone": self.generate_conditional_phone("随机", rng=rng),
            "email": f"{employee_no.lower()}@{email_domain}",
            "company": self._generate_company_name(rng, fake),
            "id_card": self.generate_random_id_card(region["province"], gender, 22, 50, rng=rng, reference_date=base_now),
            "hire_date": (
                base_now - datetime.timedelta(days=rng.randint(30, 3650))
            ).strftime("%Y-%m-%d"),
            "province": region["province"],
            "city": region["city"],
        }

    def _build_shipping_record(self, index: int, rng, fake, base_now: datetime.datetime, batch_token: str,
                               email_domain: str) -> Dict[str, Any]:
        region = self._choose_region(rng)
        gender = rng.choice(["男", "女"])
        return {
            "scenario": "收货地址簿",
            "batch_tag": batch_token,
            "address_id": f"ADDR-{batch_token.upper()}-{index:03d}",
            "receiver_name": self._generate_name(rng, fake, gender),
            "receiver_phone": self.generate_conditional_phone("随机", rng=rng),
            "province": region["province"],
            "city": region["city"],
            "district_area_code": region["area_code"],
            "address": self.generate_random_address(region["province"], region["city"], detailed=True, rng=rng),
            "postcode": f"{rng.randint(100000, 999999)}",
            "label": rng.choice(ADDRESS_LABELS),
            "is_default": "是" if index == 1 else rng.choice(["是", "否", "否"]),
            "updated_at": self._generate_datetime_string(rng, base_now, max_days_back=30),
        }

    def _build_order_record(self, index: int, rng, fake, base_now: datetime.datetime, batch_token: str,
                            email_domain: str) -> Dict[str, Any]:
        order_amount = round(rng.uniform(19.9, 4999.0), 2)
        discount_amount = round(min(order_amount * rng.choice([0, 0.05, 0.1, 0.15]), order_amount), 2)
        pay_status = rng.choice(PAY_STATUSES)
        order_status = (
            "待支付" if pay_status == "待支付" else
            "已取消" if pay_status == "已退款" else
            rng.choice(["待发货", "待收货", "已完成"])
        )
        created_time = base_now - datetime.timedelta(days=rng.randint(0, 45), minutes=rng.randint(0, 1440))
        pay_time = "" if pay_status == "待支付" else (
            created_time + datetime.timedelta(minutes=rng.randint(1, 360))
        ).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "scenario": "订单支付记录",
            "batch_tag": batch_token,
            "order_no": f"ORD{base_now.strftime('%Y%m%d')}{batch_token.upper()}{index:04d}",
            "user_no": f"U{batch_token.upper()}{rng.randint(1000, 9999)}",
            "product_name": rng.choice(COMMON_PRODUCTS),
            "order_amount": f"{order_amount:.2f}",
            "discount_amount": f"{discount_amount:.2f}",
            "pay_amount": f"{max(order_amount - discount_amount, 0):.2f}",
            "pay_status": pay_status,
            "order_status": order_status,
            "created_at": created_time.strftime("%Y-%m-%d %H:%M:%S"),
            "pay_time": pay_time,
            "remark": rng.choice(["联调用例", "回归测试", "压测预置数据", "对账验证", "退款校验"]),
        }

    def generate_boundary_test_cases(self, field_type: str, seed: Optional[int] = None,
                                     min_length: int = 2, max_length: int = 20,
                                     amount_min: float = 0.0, amount_max: float = 99999.99,
                                     email_domain: str = "example.com",
                                     include_valid: bool = True, include_boundary: bool = True,
                                     include_invalid: bool = True) -> List[Dict[str, Any]]:
        """生成常用字段的正常值、边界值和异常值。"""
        rng, _, base_now = self._get_random_context(seed)
        records: List[Dict[str, Any]] = []
        field_code = {
            "用户名": "USERNAME",
            "密码": "PASSWORD",
            "邮箱": "EMAIL",
            "手机号": "PHONE",
            "身份证号": "IDCARD",
            "金额": "AMOUNT",
        }.get(field_type, "CASE")

        def add_case(case_name: str, case_type: str, value: Any, expected: str, note: str = ""):
            case_type_map = {
                "正常值": include_valid,
                "边界值": include_boundary,
                "异常值": include_invalid,
            }
            if not case_type_map.get(case_type, True):
                return
            records.append({
                "case_id": f"{field_code}-{len(records) + 1:02d}",
                "field_type": field_type,
                "case_name": case_name,
                "case_type": case_type,
                "value": value,
                "expected": expected,
                "note": note,
            })

        min_length = max(1, min_length)
        max_length = max(min_length, max_length)

        if field_type == "用户名":
            normal_value = self.generate_random_string(max(min_length + 4, 6), ["小写字母", "数字"], rng=rng)
            add_case("常规可用用户名", "正常值", normal_value, "应通过", "仅包含小写字母和数字")
            add_case("最小长度边界", "边界值",
                     self.generate_random_string(min_length, ["小写字母", "数字"], rng=rng), "应通过")
            add_case("最大长度边界", "边界值",
                     self.generate_random_string(max_length, ["小写字母", "数字"], rng=rng), "应通过")
            add_case("空字符串", "异常值", "", "应拒绝", "模拟必填项为空")
            add_case("长度不足", "异常值",
                     self.generate_random_string(max(min_length - 1, 1), ["小写字母"], rng=rng), "应拒绝")
            add_case("长度超限", "异常值",
                     self.generate_random_string(max_length + 1, ["小写字母"], rng=rng), "应拒绝")
            add_case("包含空格", "异常值", "qa user", "应拒绝", "命中非法空白字符")
            add_case("包含特殊字符", "异常值", "qa_user@", "应拒绝", "命中非法特殊字符")

        elif field_type == "密码":
            options = ["包含小写字母", "包含大写字母", "包含数字", "包含特殊字符"]
            safe_min = max(min_length, 8)
            add_case("强密码示例", "正常值", self.generate_random_password(max(safe_min + 2, 10), options, rng=rng),
                     "应通过")
            add_case("最小长度边界", "边界值", self.generate_random_password(safe_min, options, rng=rng), "应通过")
            add_case("最大长度边界", "边界值", self.generate_random_password(max_length, options, rng=rng), "应通过")
            add_case("缺少大写字母", "异常值", "password1!", "应拒绝")
            add_case("缺少数字", "异常值", "Password!", "应拒绝")
            add_case("缺少特殊字符", "异常值", "Password1", "应拒绝")
            add_case("长度不足", "异常值", "Aa1!", "应拒绝")
            add_case("包含空格", "异常值", "Pass word1!", "应拒绝")

        elif field_type == "邮箱":
            local_part = self.generate_random_string(8, ["小写字母", "数字"], rng=rng)
            add_case("常规邮箱", "正常值", f"{local_part}@{email_domain}", "应通过")
            add_case("子域名邮箱", "边界值", f"{local_part}@qa.{email_domain}", "应通过")
            add_case("缺少@", "异常值", f"{local_part}{email_domain}", "应拒绝")
            add_case("缺少域名", "异常值", f"{local_part}@", "应拒绝")
            add_case("连续两个@", "异常值", f"{local_part}@@{email_domain}", "应拒绝")
            add_case("含中文字符", "异常值", f"测试{local_part}@{email_domain}", "应拒绝")
            add_case("包含空格", "异常值", f"{local_part} @{email_domain}", "应拒绝")

        elif field_type == "手机号":
            add_case("常规手机号", "正常值", self.generate_conditional_phone("随机", rng=rng), "应通过")
            add_case("号段边界示例", "边界值", "13000000000", "应通过", "常见联通号段")
            add_case("长度不足", "异常值", "1380013800", "应拒绝")
            add_case("长度超限", "异常值", "138001380000", "应拒绝")
            add_case("非法号段", "异常值", "10100138000", "应拒绝")
            add_case("含字母", "异常值", "13800ABC000", "应拒绝")
            add_case("空字符串", "异常值", "", "应拒绝")

        elif field_type == "身份证号":
            valid_id = self.generate_random_id_card("北京市", "随机", 18, 45, rng=rng, reference_date=base_now)
            add_case("常规身份证号", "正常值", valid_id, "应通过")
            add_case("最小成年年龄边界", "边界值",
                     self.generate_random_id_card("北京市", "随机", 18, 18, rng=rng, reference_date=base_now), "应通过")
            add_case("校验位错误", "异常值", self._mutate_check_code(valid_id), "应拒绝")
            add_case("长度不足", "异常值", valid_id[:-1], "应拒绝")
            add_case("包含字母", "异常值", valid_id[:6] + "ABCDEF" + valid_id[12:], "应拒绝")
            add_case("非法出生日期", "异常值", valid_id[:6] + "20240231" + valid_id[14:], "应拒绝")

        elif field_type == "金额":
            add_case("常规金额", "正常值", f"{round((amount_min + amount_max) / 2, 2):.2f}", "应通过")
            add_case("最小值边界", "边界值", f"{amount_min:.2f}", "应通过")
            add_case("最大值边界", "边界值", f"{amount_max:.2f}", "应通过")
            add_case("负数金额", "异常值", f"{-abs(max(amount_min, 1.0)):.2f}", "应拒绝")
            add_case("超出上限", "异常值", f"{amount_max + 0.01:.2f}", "应拒绝")
            add_case("超出小数精度", "异常值", "88.888", "应拒绝")
            add_case("非数字", "异常值", "amount_abc", "应拒绝")

        else:
            raise ValueError(f"暂不支持的字段类型: {field_type}")

        return records

    def is_faker_available(self) -> bool:
        """检查Faker是否可用"""
        return self.faker_available

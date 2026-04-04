import random
import datetime
from typing import List, Union, Dict
import streamlit as st

from qa_toolkit.config.constants import PROVINCE_CITY_AREA_CODES, LOWERCASE, UPPERCASE, PROVINCE_MAP, COUNTRY_FORMATS, \
    MOBILE_PREFIXES, UNICON_PREFIXES, TELECON_PREFIXES, BROADCAST_PREFIXES, OPERATOR_PREFIXES


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

    def safe_generate(self, generator_func, *args, **kwargs):
        """安全执行生成函数"""
        try:
            return generator_func(*args, **kwargs)
        except Exception as e:
            st.error(f"生成过程中发生错误：{e}")
            return None

    def format_profile_data(self, profile_dict: Union[Dict, str]) -> str:
        """格式化完整个人信息显示

        Args:
            profile_dict: 个人信息字典或字符串

        Returns:
            格式化后的个人信息字符串
        """
        try:
            # 如果传入的是字符串，尝试转换为字典
            if isinstance(profile_dict, str):
                try:
                    import ast
                    profile_dict = ast.literal_eval(profile_dict)
                except:
                    profile_dict = eval(profile_dict)

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

    def generate_random_string(self, length: int, chars_type: List[str]) -> str:
        """生成随机字符串

        Args:
            length: 字符串长度
            chars_type: 字符类型列表

        Returns:
            随机字符串
        """
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
        return ''.join(random.choice(chars) for _ in range(length))

    def generate_random_password(self, length: int, options: List[str]) -> str:
        """生成随机密码

        Args:
            length: 密码长度
            options: 密码选项

        Returns:
            随机密码
        """
        if self.faker_available:
            return self.fake.password(
                length=length,
                special_chars="包含特殊字符" in options,
                digits="包含数字" in options,
                upper_case="包含大写字母" in options,
                lower_case="包含小写字母" in options
            )

        # 备用方案
        password = ""
        chars = ""
        if "包含小写字母" in options:
            password += random.choice(LOWERCASE)
            chars += LOWERCASE
        if "包含大写字母" in options:
            password += random.choice(UPPERCASE)
            chars += UPPERCASE
        if "包含数字" in options:
            password += random.choice("0123456789")
            chars += "0123456789"
        if "包含特殊字符" in options:
            password += random.choice("!@#$%^&*()_+-=[]{}|;:,.<>?")
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not chars:
            password += random.choice(LOWERCASE)
            chars += "abcdefghijklmnopqrstuvwxyz0123456789"
            password += random.choice("0123456789")

        password += ''.join(random.choice(chars) for _ in range(length - len(password)))
        password_list = list(password)
        random.shuffle(password_list)
        return ''.join(password_list)

    def generate_random_phone_number(self, operator: str) -> str:
        """生成随机电话号码"""
        if self.faker_available:
            return self.fake.phone_number()

        if operator == "移动":
            prefix = random.choice(MOBILE_PREFIXES)
        elif operator == "联通":
            prefix = random.choice(UNICON_PREFIXES)
        elif operator == "电信":
            prefix = random.choice(TELECON_PREFIXES)
        elif operator == "广电":
            prefix = random.choice(BROADCAST_PREFIXES)
        else:
            rand_val = random.random()
            if rand_val < 0.35:
                prefix = random.choice(MOBILE_PREFIXES)
            elif rand_val < 0.6:
                prefix = random.choice(UNICON_PREFIXES)
            elif rand_val < 0.85:
                prefix = random.choice(TELECON_PREFIXES)
            else:
                prefix = random.choice(BROADCAST_PREFIXES)

        suffix = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        return f"{prefix}{suffix}"

    def generate_random_address(self, province: str, city: str, detailed: bool = True) -> str:
        """生成随机地址"""
        if not detailed:
            return f"{province}{city}"

        # 详细地址生成
        streets = ["中山路", "解放路", "人民路", "建设路", "和平路", "新华路", "文化路", "胜利路", "团结路", "友谊路"]
        communities = ["小区", "花园", "大厦", "公寓", "广场", "苑", "居", "湾", "城", "国际"]
        numbers = [str(i) for i in range(1, 201)]

        street = random.choice(streets)
        community = random.choice(communities)
        number = random.choice(numbers)

        return f"{province}{city}{street}{number}号{random.randint(1, 20)}栋{random.randint(1, 30)}单元{random.randint(101, 1500)}室"

    def generate_random_id_card(self, province: str, gender: str, min_age: int, max_age: int) -> str:
        """生成随机身份证号码"""

        # 1. 生成前6位地区码
        province_code = PROVINCE_MAP.get(province, "11")  # 默认北京
        area_code = province_code + ''.join([str(random.randint(0, 9)) for _ in range(4)])

        # 2. 生成出生日期码
        current_year = datetime.datetime.now().year
        birth_year = random.randint(current_year - max_age, current_year - min_age)
        birth_month = random.randint(1, 12)

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

        birth_day = random.randint(1, max_day)
        birth_date = f"{birth_year:04d}{birth_month:02d}{birth_day:02d}"

        # 3. 生成顺序码
        if gender == "男":
            sequence = random.randint(1, 499) * 2 + 1
        elif gender == "女":
            sequence = random.randint(0, 499) * 2
        else:  # 随机
            sequence = random.randint(0, 999)
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

    def generate_conditional_phone(self, operator: str) -> str:
        """生成手机号码（仅匹配运营商号段）"""

        # 如果选择"随机"，则从所有运营商中随机选择
        if operator == "随机":
            all_prefixes = []
            for op in OPERATOR_PREFIXES.values():
                all_prefixes.extend(op)
            prefix = random.choice(all_prefixes)
        else:
            prefix = random.choice(OPERATOR_PREFIXES[operator])

        # 生成后8位数字（总长度=11位）
        suffix = ''.join([str(random.randint(0, 9)) for _ in range(11 - len(prefix))])
        return f"{prefix}{suffix}"

    def generate_landline_number(self, operator: str = None, area_code: str = None) -> str:
        """生成座机号码（区号可选）"""
        # 1. 区号生成逻辑
        if not area_code:
            # 从完整的省份城市映射中随机选择一个区号
            all_area_codes = []
            for province, cities in PROVINCE_CITY_AREA_CODES.items():
                for city, code in cities.items():
                    all_area_codes.append(code)

            # 去重并确保有可用的区号
            if all_area_codes:
                area_code = random.choice(all_area_codes)
            else:
                # 备用区号列表
                backup_area_codes = [
                    '010', '021', '022', '023', '020', '024',  # 三位区号
                    '025', '027', '028', '029',  # 省会城市
                    '0512', '0516', '0571', '0574', '0755', '0757'  # 其他常见城市
                ]
                area_code = random.choice(backup_area_codes)

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
        first_digit = random.randint(2, 9)

        # 剩余位数
        if local_length == 8:
            # 8位号码格式：PQR + ABCD 或 PQ + ABCDE
            remaining_length = 7
            remaining = str(random.randint(0, 10 ** remaining_length - 1)).zfill(remaining_length)
            local_number = str(first_digit) + remaining
        else:
            # 7位号码格式：P + ABCDEF
            remaining_length = 6
            remaining = str(random.randint(0, 10 ** remaining_length - 1)).zfill(remaining_length)
            local_number = str(first_digit) + remaining

        # 4. 格式化输出
        return f"0{area_code}-{local_number}" if not area_code.startswith('0') else f"{area_code}-{local_number}"

    def generate_international_phone(self, country: str) -> str:
        """生成国际手机号码"""
        if country not in COUNTRY_FORMATS:
            # 默认格式
            country_info = {"code": "+1", "format": ["###-###-####"]}
        else:
            country_info = COUNTRY_FORMATS[country]

        # 选择一种格式
        format_pattern = random.choice(country_info["format"])

        # 生成号码
        phone_number = ""
        for char in format_pattern:
            if char == "#":
                phone_number += str(random.randint(0, 9))
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

    def generate_random_email(self, domain_option: str, custom_domain: str, selected_domains: List[str]) -> str:
        """生成随机邮箱"""
        username_length = random.randint(5, 12)
        username = ''.join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(username_length))

        if domain_option == "自定义域名":
            domain = custom_domain
        else:
            domain = random.choice(selected_domains) if selected_domains else random.choice(["gmail.com", "yahoo.com"])

        return f"{username}@{domain}"

    def is_faker_available(self) -> bool:
        """检查Faker是否可用"""
        return self.faker_available

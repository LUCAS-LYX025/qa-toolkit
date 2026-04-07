"""
基础数据常量模块
用于存储省份、城市、国家、分类等基础数据
"""

# 省份和直辖市数据
PROVINCES = {
    "北京市": ["北京市"],
    "天津市": ["天津市"],
    "上海市": ["上海市"],
    "重庆市": ["重庆市"],
    "河北省": ["石家庄市", "唐山市", "秦皇岛市", "邯郸市", "邢台市", "保定市", "张家口市", "承德市", "沧州市", "廊坊市", "衡水市"],
    "山西省": ["太原市", "大同市", "阳泉市", "长治市", "晋城市", "朔州市", "晋中市", "运城市", "忻州市", "临汾市", "吕梁市"],
    "内蒙古自治区": ["呼和浩特市", "包头市", "乌海市", "赤峰市", "通辽市", "鄂尔多斯市", "呼伦贝尔市", "巴彦淖尔市", "乌兰察布市", "兴安盟", "锡林郭勒盟", "阿拉善盟"],
    "辽宁省": ["沈阳市", "大连市", "鞍山市", "抚顺市", "本溪市", "丹东市", "锦州市", "营口市", "阜新市", "辽阳市", "盘锦市", "铁岭市", "朝阳市", "葫芦岛市"],
    "吉林省": ["长春市", "吉林市", "四平市", "辽源市", "通化市", "白山市", "松原市", "白城市", "延边朝鲜族自治州"],
    "黑龙江省": ["哈尔滨市", "齐齐哈尔市", "鸡西市", "鹤岗市", "双鸭山市", "大庆市", "伊春市", "佳木斯市", "七台河市", "牡丹江市", "黑河市", "绥化市", "大兴安岭地区"],
    "江苏省": ["南京市", "无锡市", "徐州市", "常州市", "苏州市", "南通市", "连云港市", "淮安市", "盐城市", "扬州市", "镇江市", "泰州市", "宿迁市"],
    "浙江省": ["杭州市", "宁波市", "温州市", "嘉兴市", "湖州市", "绍兴市", "金华市", "衢州市", "舟山市", "台州市", "丽水市"],
    "安徽省": ["合肥市", "芜湖市", "蚌埠市", "淮南市", "马鞍山市", "淮北市", "铜陵市", "安庆市", "黄山市", "滁州市", "阜阳市", "宿州市", "六安市", "亳州市", "池州市",
            "宣城市"],
    "福建省": ["福州市", "厦门市", "莆田市", "三明市", "泉州市", "漳州市", "南平市", "龙岩市", "宁德市"],
    "江西省": ["南昌市", "景德镇市", "萍乡市", "九江市", "新余市", "鹰潭市", "赣州市", "吉安市", "宜春市", "抚州市", "上饶市"],
    "山东省": ["济南市", "青岛市", "淄博市", "枣庄市", "东营市", "烟台市", "潍坊市", "济宁市", "泰安市", "威海市", "日照市", "临沂市", "德州市", "聊城市", "滨州市",
            "菏泽市"],
    "河南省": ["郑州市", "开封市", "洛阳市", "平顶山市", "安阳市", "鹤壁市", "新乡市", "焦作市", "濮阳市", "许昌市", "漯河市", "三门峡市", "南阳市", "商丘市", "信阳市",
            "周口市", "驻马店市"],
    "湖北省": ["武汉市", "黄石市", "十堰市", "宜昌市", "襄阳市", "鄂州市", "荆门市", "孝感市", "荆州市", "黄冈市", "咸宁市", "随州市", "恩施土家族苗族自治州"],
    "湖南省": ["长沙市", "株洲市", "湘潭市", "衡阳市", "邵阳市", "岳阳市", "常德市", "张家界市", "益阳市", "郴州市", "永州市", "怀化市", "娄底市", "湘西土家族苗族自治州"],
    "广东省": ["广州市", "深圳市", "珠海市", "汕头市", "佛山市", "韶关市", "湛江市", "肇庆市", "江门市", "茂名市", "惠州市", "梅州市", "汕尾市", "河源市", "阳江市",
            "清远市", "东莞市", "中山市", "潮州市", "揭阳市", "云浮市"],
    "广西壮族自治区": ["南宁市", "柳州市", "桂林市", "梧州市", "北海市", "防城港市", "钦州市", "贵港市", "玉林市", "百色市", "贺州市", "河池市", "来宾市", "崇左市"],
    "海南省": ["海口市", "三亚市", "三沙市", "儋州市"],
    "四川省": ["成都市", "自贡市", "攀枝花市", "泸州市", "德阳市", "绵阳市", "广元市", "遂宁市", "内江市", "乐山市", "南充市", "眉山市", "宜宾市", "广安市", "达州市",
            "雅安市", "巴中市", "资阳市", "阿坝藏族羌族自治州", "甘孜藏族自治州", "凉山彝族自治州"],
    "贵州省": ["贵阳市", "六盘水市", "遵义市", "安顺市", "毕节市", "铜仁市", "黔西南布依族苗族自治州", "黔东南苗族侗族自治州", "黔南布依族苗族自治州"],
    "云南省": ["昆明市", "曲靖市", "玉溪市", "保山市", "昭通市", "丽江市", "普洱市", "临沧市", "楚雄彝族自治州", "红河哈尼族彝族自治州", "文山壮族苗族自治州", "西双版纳傣族自治州",
            "大理白族自治州", "德宏傣族景颇族自治州", "怒江傈僳族自治州", "迪庆藏族自治州"],
    "西藏自治区": ["拉萨市", "日喀则市", "昌都市", "林芝市", "山南市", "那曲市", "阿里地区"],
    "陕西省": ["西安市", "铜川市", "宝鸡市", "咸阳市", "渭南市", "延安市", "汉中市", "榆林市", "安康市", "商洛市"],
    "甘肃省": ["兰州市", "嘉峪关市", "金昌市", "白银市", "天水市", "武威市", "张掖市", "平凉市", "酒泉市", "庆阳市", "定西市", "陇南市", "临夏回族自治州", "甘南藏族自治州"],
    "青海省": ["西宁市", "海东市", "海北藏族自治州", "黄南藏族自治州", "海南藏族自治州", "果洛藏族自治州", "玉树藏族自治州", "海西蒙古族藏族自治州"],
    "宁夏回族自治区": ["银川市", "石嘴山市", "吴忠市", "固原市", "中卫市"],
    "新疆维吾尔自治区": ["乌鲁木齐市", "克拉玛依市", "吐鲁番市", "哈密市", "昌吉回族自治州", "博尔塔拉蒙古自治州", "巴音郭楞蒙古自治州", "阿克苏地区", "克孜勒苏柯尔克孜自治州", "喀什地区",
                 "和田地区", "伊犁哈萨克自治州", "塔城地区", "阿勒泰地区"],
    "台湾省": ["台北市", "新北市", "桃园市", "台中市", "台南市", "高雄市"],
    "香港特别行政区": ["香港岛", "九龙", "新界"],
    "澳门特别行政区": ["澳门半岛", "氹仔", "路环"],
    "随机": ["随机"]
}
# 省份城市区域映射
PROVINCE_CITY_AREA_CODES = {
    "北京市": {
        "北京市": "010"
    },
    "上海市": {
        "上海市": "021"
    },
    "天津市": {
        "天津市": "022"
    },
    "重庆市": {
        "重庆市": "023"
    },
    "广东省": {
        "广州市": "020",
        "深圳市": "0755",
        "东莞市": "0769",
        "佛山市": "0757",
        "中山市": "0760",
        "珠海市": "0756",
        "惠州市": "0752",
        "江门市": "0750",
        "汕头市": "0754",
        "湛江市": "0759",
        "肇庆市": "0758",
        "茂名市": "0668",
        "韶关市": "0751",
        "潮州市": "0768",
        "揭阳市": "0663",
        "汕尾市": "0660",
        "阳江市": "0662",
        "清远市": "0763",
        "梅州市": "0753",
        "河源市": "0762",
        "云浮市": "0766"
    },
    "江苏省": {
        "南京市": "025",
        "苏州市": "0512",
        "无锡市": "0510",
        "常州市": "0519",
        "徐州市": "0516",
        "南通市": "0513",
        "扬州市": "0514",
        "盐城市": "0515",
        "淮安市": "0517",
        "连云港市": "0518",
        "镇江市": "0511",
        "泰州市": "0523",
        "宿迁市": "0527"
    },
    "浙江省": {
        "杭州市": "0571",
        "宁波市": "0574",
        "温州市": "0577",
        "嘉兴市": "0573",
        "湖州市": "0572",
        "绍兴市": "0575",
        "金华市": "0579",
        "衢州市": "0570",
        "舟山市": "0580",
        "台州市": "0576",
        "丽水市": "0578"
    },
    "山东省": {
        "济南市": "0531",
        "青岛市": "0532",
        "淄博市": "0533",
        "枣庄市": "0632",
        "东营市": "0546",
        "烟台市": "0535",
        "潍坊市": "0536",
        "济宁市": "0537",
        "泰安市": "0538",
        "威海市": "0631",
        "日照市": "0633",
        "临沂市": "0539",
        "德州市": "0534",
        "聊城市": "0635",
        "滨州市": "0543",
        "菏泽市": "0530"
    },
    "四川省": {
        "成都市": "028",
        "绵阳市": "0816",
        "德阳市": "0838",
        "南充市": "0817",
        "宜宾市": "0831",
        "泸州市": "0830",
        "达州市": "0818",
        "乐山市": "0833",
        "内江市": "0832",
        "自贡市": "0813",
        "攀枝花市": "0812",
        "广安市": "0826",
        "遂宁市": "0825",
        "广元市": "0839",
        "眉山市": "0833",
        "资阳市": "0832",
        "雅安市": "0835",
        "巴中市": "0827"
    },
    "湖北省": {
        "武汉市": "027",
        "黄石市": "0714",
        "十堰市": "0719",
        "宜昌市": "0717",
        "襄阳市": "0710",
        "鄂州市": "0711",
        "荆门市": "0724",
        "孝感市": "0712",
        "荆州市": "0716",
        "黄冈市": "0713",
        "咸宁市": "0715",
        "随州市": "0722"
    },
    "湖南省": {
        "长沙市": "0731",
        "株洲市": "0731",
        "湘潭市": "0731",
        "衡阳市": "0734",
        "邵阳市": "0739",
        "岳阳市": "0730",
        "常德市": "0736",
        "张家界市": "0744",
        "益阳市": "0737",
        "郴州市": "0735",
        "永州市": "0746",
        "怀化市": "0745",
        "娄底市": "0738"
    },
    "河南省": {
        "郑州市": "0371",
        "开封市": "0371",
        "洛阳市": "0379",
        "平顶山市": "0375",
        "安阳市": "0372",
        "鹤壁市": "0392",
        "新乡市": "0373",
        "焦作市": "0391",
        "濮阳市": "0393",
        "许昌市": "0374",
        "漯河市": "0395",
        "三门峡市": "0398",
        "南阳市": "0377",
        "商丘市": "0370",
        "信阳市": "0376",
        "周口市": "0394",
        "驻马店市": "0396"
    },
    "河北省": {
        "石家庄市": "0311",
        "唐山市": "0315",
        "秦皇岛市": "0335",
        "邯郸市": "0310",
        "邢台市": "0319",
        "保定市": "0312",
        "张家口市": "0313",
        "承德市": "0314",
        "沧州市": "0317",
        "廊坊市": "0316",
        "衡水市": "0318"
    },
    "辽宁省": {
        "沈阳市": "024",
        "大连市": "0411",
        "鞍山市": "0412",
        "抚顺市": "0413",
        "本溪市": "0414",
        "丹东市": "0415",
        "锦州市": "0416",
        "营口市": "0417",
        "阜新市": "0418",
        "辽阳市": "0419",
        "盘锦市": "0427",
        "铁岭市": "0410",
        "朝阳市": "0421",
        "葫芦岛市": "0429"
    },
    "陕西省": {
        "西安市": "029",
        "铜川市": "0919",
        "宝鸡市": "0917",
        "咸阳市": "0910",
        "渭南市": "0913",
        "延安市": "0911",
        "汉中市": "0916",
        "榆林市": "0912",
        "安康市": "0915",
        "商洛市": "0914"
    },
    "福建省": {
        "福州市": "0591",
        "厦门市": "0592",
        "莆田市": "0594",
        "三明市": "0598",
        "泉州市": "0595",
        "漳州市": "0596",
        "南平市": "0599",
        "龙岩市": "0597",
        "宁德市": "0593"
    },
    "安徽省": {
        "合肥市": "0551",
        "芜湖市": "0553",
        "蚌埠市": "0552",
        "淮南市": "0554",
        "马鞍山市": "0555",
        "淮北市": "0561",
        "铜陵市": "0562",
        "安庆市": "0556",
        "黄山市": "0559",
        "滁州市": "0550",
        "阜阳市": "0558",
        "宿州市": "0557",
        "六安市": "0564",
        "亳州市": "0558",
        "池州市": "0566",
        "宣城市": "0563"
    }
}

# 国家列表
COUNTRIES = [
    "日本", "韩国", "印度", "新加坡", "马来西亚", "泰国", "越南", "菲律宾", "印度尼西亚",
    "香港", "台湾", "澳门", "英国", "德国", "法国", "意大利", "西班牙", "俄罗斯", "荷兰",
    "瑞士", "瑞典", "挪威", "丹麦", "芬兰", "比利时", "奥地利", "爱尔兰", "葡萄牙", "希腊",
    "波兰", "捷克", "匈牙利", "美国", "加拿大", "墨西哥", "巴西", "阿根廷", "智利", "哥伦比亚",
    "秘鲁", "南非", "埃及", "尼日利亚", "肯尼亚", "摩洛哥", "澳大利亚", "新西兰", "阿联酋",
    "沙特阿拉伯", "以色列", "土耳其", "卡塔尔"
]

# 国际号码格式定义（国家代码 + 手机号格式）
COUNTRY_FORMATS = {
    # 亚洲
    "日本": {
        "code": "+81",
        "format": ["90-####-####", "80-####-####", "70-####-####"]
    },
    "韩国": {
        "code": "+82",
        "format": ["10-####-####", "16-####-####", "19-####-####"]
    },
    "印度": {
        "code": "+91",
        "format": ["9#########", "8#########", "7#########"]
    },
    "新加坡": {
        "code": "+65",
        "format": ["9### ####", "8### ####", "6### ####"]
    },
    "马来西亚": {
        "code": "+60",
        "format": ["12-### ####", "13-### ####", "16-### ####"]
    },
    "泰国": {
        "code": "+66",
        "format": ["8#-###-####", "9#-###-####", "6#-###-####"]
    },
    "越南": {
        "code": "+84",
        "format": ["9#-####-###", "8#-####-###", "3#-####-###"]
    },
    "菲律宾": {
        "code": "+63",
        "format": ["9##-###-####", "8##-###-####", "2##-###-####"]
    },
    "印度尼西亚": {
        "code": "+62",
        "format": ["8##-####-###", "8##-###-####"]
    },
    "香港": {
        "code": "+852",
        "format": ["5### ####", "6### ####", "9### ####"]
    },
    "台湾": {
        "code": "+886",
        "format": ["9## ### ###", "9########", "4## ### ###"]
    },
    "澳门": {
        "code": "+853",
        "format": ["6### ####", "5### ####"]
    },

    # 欧洲
    "英国": {
        "code": "+44",
        "format": ["7### ######", "7########", "20-####-####"]
    },
    "德国": {
        "code": "+49",
        "format": ["15## #######", "17## #######", "16## #######"]
    },
    "法国": {
        "code": "+33",
        "format": ["6 ## ## ## ##", "7 ## ## ## ##", "1 ## ## ## ##"]
    },
    "意大利": {
        "code": "+39",
        "format": ["3## #######", "3##########"]
    },
    "西班牙": {
        "code": "+34",
        "format": ["6## ### ###", "7## ### ###"]
    },
    "俄罗斯": {
        "code": "+7",
        "format": ["9## ###-##-##", "9##########", "8## ###-##-##"]
    },
    "荷兰": {
        "code": "+31",
        "format": ["6-####-####", "6########"]
    },
    "瑞士": {
        "code": "+41",
        "format": ["7# ### ## ##", "7########"]
    },
    "瑞典": {
        "code": "+46",
        "format": ["7#-### ## ##", "7########"]
    },
    "挪威": {
        "code": "+47",
        "format": ["4## ## ###", "9## ## ###"]
    },
    "丹麦": {
        "code": "+45",
        "format": ["## ## ## ##", "########"]
    },
    "芬兰": {
        "code": "+358",
        "format": ["4# ### ## ##", "4########"]
    },
    "比利时": {
        "code": "+32",
        "format": ["4## ## ## ##", "4########"]
    },
    "奥地利": {
        "code": "+43",
        "format": ["6## #######", "6##########"]
    },
    "爱尔兰": {
        "code": "+353",
        "format": ["8# #######", "8##########"]
    },
    "葡萄牙": {
        "code": "+351",
        "format": ["9## ### ###", "9########"]
    },
    "希腊": {
        "code": "+30",
        "format": ["69## ######", "69########"]
    },
    "波兰": {
        "code": "+48",
        "format": ["### ### ###", "##########"]
    },
    "捷克": {
        "code": "+420",
        "format": ["### ### ###", "##########"]
    },
    "匈牙利": {
        "code": "+36",
        "format": ["20/###-####", "30/###-####"]
    },

    # 北美洲
    "美国": {
        "code": "+1",
        "format": ["###-###-####", "(###) ###-####", "###.###.####"]
    },
    "加拿大": {
        "code": "+1",
        "format": ["###-###-####", "(###) ###-####", "###.###.####"]
    },
    "墨西哥": {
        "code": "+52",
        "format": ["1 ## ## ## ####", "1###########"]
    },

    # 南美洲
    "巴西": {
        "code": "+55",
        "format": ["## 9####-####", "## 8####-####", "## 7####-####"]
    },
    "阿根廷": {
        "code": "+54",
        "format": ["9 ## ####-####", "11 ####-####"]
    },
    "智利": {
        "code": "+56",
        "format": ["9 #### ####", "2 #### ####"]
    },
    "哥伦比亚": {
        "code": "+57",
        "format": ["3## #######", "3##########"]
    },
    "秘鲁": {
        "code": "+51",
        "format": ["9## ### ###", "9########"]
    },

    # 非洲
    "南非": {
        "code": "+27",
        "format": ["## ### ####", "##########"]
    },
    "埃及": {
        "code": "+20",
        "format": ["1## #######", "1##########"]
    },
    "尼日利亚": {
        "code": "+234",
        "format": ["### ### ####", "###########"]
    },
    "肯尼亚": {
        "code": "+254",
        "format": ["7## #######", "7##########"]
    },
    "摩洛哥": {
        "code": "+212",
        "format": ["6-##-##-##-##", "6##########"]
    },

    # 大洋洲
    "澳大利亚": {
        "code": "+61",
        "format": ["4## ### ###", "4########", "2 #### ####"]
    },
    "新西兰": {
        "code": "+64",
        "format": ["2# ### ####", "2##########"]
    },

    # 中东
    "阿联酋": {
        "code": "+971",
        "format": ["5# ### ####", "5##########"]
    },
    "沙特阿拉伯": {
        "code": "+966",
        "format": ["5# ### ####", "5##########"]
    },
    "以色列": {
        "code": "+972",
        "format": ["5#-###-####", "5##########"]
    },
    "土耳其": {
        "code": "+90",
        "format": ["5## ### ####", "5##########"]
    },
    "卡塔尔": {
        "code": "+974",
        "format": ["3### ####", "5### ####", "7### ####"]
    }
}

# 分类数据
CATEGORIES = {
    "人物信息": ["随机姓名", "随机姓", "随机名", "男性姓名", "女性姓名", "完整个人信息"],
    "地址信息": ["随机地址", "随机城市", "随机国家", "随机邮编", "随机街道"],
    "网络信息": ["随机邮箱", "安全邮箱", "公司邮箱", "免费邮箱", "随机域名", "随机URL", "随机IP地址", "随机用户代理"],
    "公司信息": ["随机公司名", "公司后缀", "职位"],
    "金融信息": ["信用卡号", "信用卡提供商", "信用卡有效期", "货币"],
    "日期时间": ["随机日期时间", "随机日期", "随机时间", "今年日期", "本月日期"],
    "文本内容": ["随机单词", "随机句子", "随机段落", "随机文本"],
    "电话号码": ["随机手机号", "号段前缀"],
    "其他信息": ["随机颜色", "随机UUID", "随机MD5", "随机SHA1", "随机文件扩展名", "随机MIME类型"]
}

# 省份代码映射
PROVINCE_MAP = {
    "北京市": "11", "天津市": "12", "河北省": "13", "山西省": "14",
    "内蒙古自治区": "15", "辽宁省": "21", "吉林省": "22", "黑龙江省": "23",
    "上海市": "31", "浙江省": "33", "安徽省": "34", "福建省": "35",
    "江西省": "36", "山东省": "37", "河南省": "41", "湖北省": "42",
    "湖南省": "43", "广东省": "44", "广西壮族自治区": "45", "海南省": "46",
    "重庆市": "50", "四川省": "51", "贵州省": "52", "云南省": "53",
    "西藏自治区": "54", "陕西省": "61", "甘肃省": "62", "青海省": "63",
    "宁夏回族自治区": "64", "新疆维吾尔自治区": "65"
}

# 运营商前缀
MOBILE_PREFIXES = ["134", "135", "136", "137", "138", "139", "147", "150", "151", "152", "157", "158", "159",
                   "172", "178", "182", "183", "184", "187", "188", "198", "1703", "1705", "1706"]
UNICON_PREFIXES = ["130", "131", "132", "145", "155", "156", "166", "171", "175", "176", "185", "186", "1704",
                   "1707", "1708", "1709"]
TELECON_PREFIXES = ["133", "153", "173", "177", "180", "181", "189", "191", "193", "199", "1700", "1701",
                    "1702"]
BROADCAST_PREFIXES = ["192", "190", "196", "197"]
OPERATOR_PREFIXES = {
    "移动": MOBILE_PREFIXES,
    "联通": UNICON_PREFIXES,
    "电信": TELECON_PREFIXES,
    "广电": BROADCAST_PREFIXES
}

# 全局单位换算映射表
TO_SECONDS = {
    "毫秒": 0.001,
    "秒": 1,
    "分钟": 60,
    "小时": 3600,
    "天": 86400,
    "周": 604800,
    "月": 2592000,
    "年": 31536000
}

# === 常量定义 === #
RANDOM_STRING_TYPES = ["小写字母", "大写字母", "数字", "特殊字符"]
PASSWORD_OPTIONS = ["包含小写字母", "包含大写字母", "包含数字", "包含特殊字符"]
DOMAINS_PRESET = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "163.com", "qq.com"]
PHONE_TYPES = ["手机号", "座机", "国际号码"]
GENDERS = ["随机", "男", "女"]
# 小写字母
LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
# 大写字母
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# 工具类别定义
TOOL_CATEGORIES = {
    "数据生成工具": {
        "icon": "🎲",
        "description": "生成测试数据、随机内容、模拟用户信息",
        "color": "#667eea"
    },
    "测试用例生成器": {
        "icon": "🧪",
        "description": "AI生成测试用例，支持导出用例",
        "color": "#ed64a6"
    },
    "禅道绩效统计": {
        "icon": "📈",
        "description": "禅道数据统计、绩效分析、报告生成",
        "color": "#4CAF50"
    },
    "日志分析工具": {
        "icon": "📋",
        "description": "日志解析、级别统计、模式识别",
        "color": "#4299e1"
    },
    "BI数据分析工具": {
        "icon": "📊",
        "description": "商业智能数据分析"
    },
    "文本对比工具": {
        "icon": "🔍",
        "description": "文本差异比较、规范化对比、Diff 导出",
        "color": "#ed8936"
    },
    "字数统计工具": {
        "icon": "📝",
        "description": "文本分析、字符统计、频率分析",
        "color": "#48bb78"
    },
    "正则测试工具": {
        "icon": "⚡",
        "description": "正则测试、模式匹配、替换操作",
        "color": "#9f7aea"
    },
    "加密/解密工具": {
        "icon": "🔐",
        "description": "各种加密解密算法工具",
        "color": "#ed64a6"
    },
    "JSON处理工具": {
        "icon": "👨‍💻",
        "description": "JSON格式验证、差异比较、数据解析",
        "color": "#f56565"
    },
    "时间处理工具": {
        "icon": "⏰",
        "description": "时间转换、日期计算、时间分析",
        "color": "#38b2ac"
    },
    "图片处理工具": {
        "icon": "🖼️",
        "description": "格式转换、压缩、尺寸调整，加水印",
        "color": "#ed64a6"
    },
    "IP/域名查询工具": {
        "icon": "🌐",
        "description": "IP定位、域名解析、网络信息查询",
        "color": "#ed64a6"
    },
    "接口性能测试": {
        "icon": "🚀",
        "description": "JMeter风格接口压测、CSV参数化、事务链路",
        "color": "#dd6b20"
    },
    "接口安全测试": {
        "icon": "🛡️",
        "description": "API/移动端/Web 安全审计、基线探测、清单和报告",
        "color": "#15803d"
    },
    "接口研发辅助": {
        "icon": "🛠️",
        "description": "接口变更分析、Mock服务、调试代码生成",
        "color": "#3182ce"
    },
    "接口自动化测试": {
        "icon": "🤖",
        "description": "基于接口文档自动生成和执行测试用例"
    },
}

# # CSS样式
CSS_STYLES = """
<style>
    :root {
        --qa-btn-primary-start: #071427;
        --qa-btn-primary-mid: #13294b;
        --qa-btn-primary-end: #224d79;
        --qa-btn-primary-shadow: rgba(7, 20, 39, 0.26);
        --qa-btn-primary-border: rgba(250, 204, 21, 0.22);
        --qa-btn-primary-light: linear-gradient(135deg, #fff6d5 0%, #f5edd0 50%, #e7eef8 100%);
        --qa-btn-primary-light-border: rgba(250, 204, 21, 0.24);
        --qa-btn-secondary-text: #13294b;
        --qa-btn-secondary-border: rgba(250, 204, 21, 0.18);
        --qa-btn-secondary-shadow: rgba(7, 20, 39, 0.10);
        --qa-btn-secondary-surface: linear-gradient(135deg, #10233f 0%, #17345c 62%, #2a5788 100%);
        --qa-btn-download-surface: linear-gradient(135deg, #fb923c 0%, #ea580c 52%, #7c2d12 100%);
        --qa-btn-download-light: linear-gradient(135deg, #fff1c7 0%, #ffd9a1 52%, #f7ecda 100%);
        --qa-btn-download-border: rgba(251, 146, 60, 0.28);
        --qa-btn-download-light-border: rgba(234, 88, 12, 0.24);
        --qa-btn-download-shadow: rgba(124, 45, 18, 0.24);
        --qa-surface-border: #d5dce8;
        --qa-surface-border-strong: #c7a44f;
        --qa-surface-panel: linear-gradient(145deg, #f7f9fd 0%, #eef3fa 56%, #f7efdf 100%);
        --qa-surface-panel-soft: linear-gradient(145deg, rgba(247,249,253,0.98) 0%, rgba(238,243,250,0.98) 56%, rgba(247,239,223,0.98) 100%);
        --qa-surface-panel-alt: linear-gradient(145deg, #fbfcff 0%, #f8f0e2 100%);
        --qa-surface-radial: radial-gradient(circle at top right, rgba(250, 204, 21, 0.10) 0%, rgba(250, 204, 21, 0) 42%);
        --qa-flow-space-xs: 0.38rem;
        --qa-flow-space-sm: 0.68rem;
        --qa-flow-space-md: 0.95rem;
        --qa-flow-space-lg: 1.32rem;
    }

    /* 全局样式 */
    .main {
        background: linear-gradient(180deg, #f7f9fd 0%, #eef3fa 58%, #f8f0e2 100%);
    }

    .main .block-container {
        padding-top: 1.15rem;
        padding-bottom: 2.35rem;
    }

    .main-header {
        font-size: 3rem;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
        text-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 1rem;
    }

    @keyframes qaHeroCurtainLeft {
        0% { transform: translateX(0) skewY(0deg); }
        100% { transform: translateX(-112%) skewY(-7deg); }
    }

    @keyframes qaHeroCurtainRight {
        0% { transform: translateX(0) skewY(0deg); }
        100% { transform: translateX(112%) skewY(7deg); }
    }

    @keyframes qaHeroGlowDrift {
        0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
        50% { transform: translate3d(10px, -14px, 0) scale(1.08); }
    }

    @keyframes qaHeroCorePulse {
        0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(250, 204, 21, 0.18); }
        50% { transform: scale(1.04); box-shadow: 0 0 0 16px rgba(250, 204, 21, 0); }
    }

    @keyframes qaHeroOrbitFloat {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-7px); }
    }

    @keyframes qaHeroScanSweep {
        0% { transform: rotate(0deg); opacity: 0.2; }
        50% { opacity: 0.8; }
        100% { transform: rotate(360deg); opacity: 0.2; }
    }

    @keyframes qaHeroTitleShimmer {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .qa-app-hero {
        position: relative;
        overflow: hidden;
        padding: 2.6rem 2rem;
        margin: -1rem -1rem 1.75rem -1rem;
        border-radius: 0 0 28px 28px;
        background:
            radial-gradient(circle at 14% 16%, rgba(250, 204, 21, 0.22), transparent 24%),
            radial-gradient(circle at 88% 18%, rgba(45, 212, 191, 0.16), transparent 22%),
            linear-gradient(160deg, #071427 0%, #13294b 48%, #09111f 100%);
        border-bottom: 1px solid rgba(250, 204, 21, 0.18);
        box-shadow: 0 22px 38px rgba(7, 20, 39, 0.20);
    }

    .qa-app-hero::before {
        content: "";
        position: absolute;
        inset: 14px;
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,0.10);
        pointer-events: none;
    }

    .qa-app-hero__curtain {
        position: absolute;
        top: -8%;
        bottom: -8%;
        width: 28%;
        z-index: 2;
        background: linear-gradient(180deg, #fb923c 0%, #ea580c 44%, #7c2d12 100%);
    }

    .qa-app-hero__curtain::after {
        content: "";
        position: absolute;
        inset: 0;
        background: repeating-linear-gradient(
            90deg,
            rgba(255,255,255,0.14) 0,
            rgba(255,255,255,0.14) 6px,
            transparent 6px,
            transparent 18px
        );
        opacity: 0.34;
    }

    .qa-app-hero__curtain--left {
        left: -4%;
        border-radius: 0 24px 24px 0;
        box-shadow: inset -12px 0 20px rgba(124, 45, 18, 0.28);
        animation: qaHeroCurtainLeft 1.18s cubic-bezier(.66,0,.2,1) forwards;
    }

    .qa-app-hero__curtain--right {
        right: -4%;
        border-radius: 24px 0 0 24px;
        box-shadow: inset 12px 0 20px rgba(124, 45, 18, 0.28);
        animation: qaHeroCurtainRight 1.18s cubic-bezier(.66,0,.2,1) forwards;
    }

    .qa-app-hero__glow {
        position: absolute;
        border-radius: 999px;
        filter: blur(10px);
        animation: qaHeroGlowDrift 4.6s ease-in-out infinite;
        pointer-events: none;
    }

    .qa-app-hero__glow--amber {
        left: 5%;
        bottom: 8%;
        width: 180px;
        height: 180px;
        background: radial-gradient(circle, rgba(250, 204, 21, 0.26), rgba(250, 204, 21, 0));
    }

    .qa-app-hero__glow--teal {
        right: 8%;
        top: 14%;
        width: 160px;
        height: 160px;
        background: radial-gradient(circle, rgba(45, 212, 191, 0.22), rgba(45, 212, 191, 0));
        animation-delay: 0.8s;
    }

    .qa-app-hero__grid {
        position: relative;
        z-index: 3;
        display: grid;
        grid-template-columns: minmax(0, 1.25fr) minmax(260px, 0.9fr);
        gap: 2rem;
        align-items: center;
    }

    .qa-app-hero__kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.9rem;
        padding: 0.38rem 0.82rem;
        border-radius: 999px;
        border: 1px solid rgba(250, 204, 21, 0.20);
        background: rgba(9, 17, 31, 0.52);
        color: #fef3c7;
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        backdrop-filter: blur(10px);
    }

    .qa-app-hero__title {
        display: inline-flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.28em;
        position: relative;
        margin: 0 0 0.8rem 0;
        padding: 0.18em 0.34em 0.24em;
        border-radius: 24px;
        font-size: clamp(2rem, 4vw, 3.35rem);
        line-height: 1.05;
        font-weight: 900;
        color: #f8fafc;
        background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
        border: 1px solid rgba(250, 204, 21, 0.16);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.14),
            0 16px 30px rgba(7, 20, 39, 0.18);
        text-shadow:
            0 2px 0 rgba(7, 20, 39, 0.28),
            0 14px 28px rgba(7, 20, 39, 0.22);
        backdrop-filter: blur(10px);
    }

    .qa-app-hero__title-main {
        color: #f8fafc;
        text-shadow:
            0 0 16px rgba(191, 219, 254, 0.16),
            0 2px 0 rgba(7, 20, 39, 0.24),
            0 14px 28px rgba(7, 20, 39, 0.22);
    }

    .qa-app-hero__title-focus {
        color: #fef3c7;
        background: linear-gradient(90deg, #fff7b2 0%, #facc15 24%, #fb923c 52%, #fef3c7 76%, #fde68a 100%);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: qaHeroTitleShimmer 6s ease-in-out infinite;
        filter: drop-shadow(0 0 14px rgba(250, 204, 21, 0.22));
        text-shadow:
            0 0 20px rgba(250, 204, 21, 0.22),
            0 2px 0 rgba(124, 45, 18, 0.20),
            0 14px 28px rgba(7, 20, 39, 0.22);
    }

    .qa-app-hero__title::after {
        content: "";
        position: absolute;
        left: 0.42em;
        right: 0.42em;
        bottom: 0.18em;
        height: 0.22em;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(250, 204, 21, 0), rgba(250, 204, 21, 0.68), rgba(45, 212, 191, 0.34), rgba(45, 212, 191, 0));
        filter: blur(4px);
        opacity: 0.84;
    }

    .qa-app-hero__desc {
        margin: 0 0 1rem 0;
        max-width: 44rem;
        color: #ffffff;
        font-size: 1.05rem;
        font-weight: 800;
        line-height: 1.8;
        text-shadow:
            0 1px 4px rgba(7, 20, 39, 0.42),
            0 0 16px rgba(15, 23, 42, 0.22);
    }

    .qa-app-hero__chip-row,
    .qa-app-hero__meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
    }

    .qa-app-hero__chip-row {
        margin-bottom: 0.9rem;
    }

    .qa-app-hero__chip,
    .qa-app-hero__meta {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        font-weight: 700;
        backdrop-filter: blur(12px);
    }

    .qa-app-hero__chip {
        padding: 0.48rem 0.82rem;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.12);
        color: #e2e8f0;
        font-size: 0.88rem;
    }

    .qa-app-hero__meta {
        padding: 0.42rem 0.74rem;
        background: rgba(15, 23, 42, 0.58);
        border: 1px solid rgba(148, 163, 184, 0.18);
        color: rgba(226, 232, 240, 0.88);
        font-size: 0.82rem;
    }

    .qa-app-hero__stage {
        position: relative;
        min-height: 260px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .qa-app-hero__stage-shell {
        position: relative;
        width: min(320px, 100%);
        aspect-ratio: 1 / 1;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .qa-app-hero__ring,
    .qa-app-hero__ring::before,
    .qa-app-hero__ring::after {
        position: absolute;
        inset: 0;
        border-radius: 50%;
        content: "";
    }

    .qa-app-hero__ring {
        border: 1px solid rgba(250, 204, 21, 0.16);
        background: radial-gradient(circle, rgba(255,255,255,0.04), rgba(255,255,255,0));
    }

    .qa-app-hero__ring::before {
        inset: 22px;
        border: 1px solid rgba(56, 189, 248, 0.16);
    }

    .qa-app-hero__ring::after {
        inset: 46px;
        border: 1px solid rgba(45, 212, 191, 0.14);
    }

    .qa-app-hero__scan {
        position: absolute;
        inset: 16px;
        border-radius: 50%;
        background: conic-gradient(
            from 0deg,
            rgba(250, 204, 21, 0) 0deg,
            rgba(250, 204, 21, 0.06) 46deg,
            rgba(45, 212, 191, 0.2) 62deg,
            rgba(45, 212, 191, 0) 82deg,
            rgba(250, 204, 21, 0) 360deg
        );
        filter: blur(2px);
        animation: qaHeroScanSweep 8.5s linear infinite;
    }

    .qa-app-hero__core {
        position: relative;
        z-index: 2;
        width: 134px;
        height: 134px;
        border-radius: 50%;
        padding: 3px;
        background: linear-gradient(135deg, #facc15 0%, #fb7185 100%);
        animation: qaHeroCorePulse 3.8s ease-in-out infinite;
        box-shadow: 0 18px 28px rgba(15, 23, 42, 0.24);
    }

    .qa-app-hero__core-inner {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.35rem;
        background:
            radial-gradient(circle at 50% 30%, rgba(255,255,255,0.16), rgba(255,255,255,0)),
            linear-gradient(180deg, #13294b 0%, #09111f 100%);
        color: #f8fafc;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.12);
    }

    .qa-app-hero__core-label {
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        color: rgba(250, 204, 21, 0.94);
    }

    .qa-app-hero__core-title {
        font-size: 1.45rem;
        font-weight: 900;
    }

    .qa-app-hero__node {
        position: absolute;
        z-index: 3;
        padding: 0.48rem 0.8rem;
        border-radius: 999px;
        background: rgba(9, 17, 31, 0.74);
        border: 1px solid rgba(255,255,255,0.12);
        color: #e2e8f0;
        font-size: 0.8rem;
        font-weight: 700;
        box-shadow: 0 10px 20px rgba(7, 20, 39, 0.18);
        animation: qaHeroOrbitFloat 4.8s ease-in-out infinite;
        white-space: nowrap;
        text-decoration: none;
        transition: transform 0.24s ease, border-color 0.24s ease, background 0.24s ease, box-shadow 0.24s ease;
    }

    .qa-app-hero__node:hover {
        transform: translateY(-3px) scale(1.03);
        border-color: rgba(250, 204, 21, 0.28);
        background: rgba(15, 23, 42, 0.88);
        box-shadow: 0 14px 28px rgba(7, 20, 39, 0.24);
    }

    .qa-app-hero__node--1 { top: 16px; left: 18px; animation-delay: 0.2s; }
    .qa-app-hero__node--2 { top: 34px; right: 6px; animation-delay: 0.8s; }
    .qa-app-hero__node--3 { bottom: 28px; left: -2px; animation-delay: 1.2s; }
    .qa-app-hero__node--4 { bottom: 10px; right: 20px; animation-delay: 1.8s; }

    .qa-app-hero__footnote {
        margin-top: 1rem;
        color: rgba(191, 219, 254, 0.82);
        font-size: 0.84rem;
        line-height: 1.7;
    }

    .sub-header {
        position: relative;
        overflow: hidden;
        margin: 1.15rem 0 1rem;
        padding: 0.95rem 1.15rem 0.95rem 1.35rem;
        border-radius: 18px;
        background:
            radial-gradient(circle at top right, rgba(250, 204, 21, 0.14), rgba(250, 204, 21, 0) 36%),
            linear-gradient(145deg, rgba(247,249,253,0.98) 0%, rgba(238,243,250,0.98) 58%, rgba(247,239,223,0.98) 100%);
        border: 1px solid rgba(199, 164, 79, 0.20);
        color: #17324a;
        font-size: 1.18rem;
        font-weight: 800;
        letter-spacing: 0.01em;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 12px 24px rgba(15, 23, 42, 0.08);
    }

    .sub-header::before {
        content: "";
        position: absolute;
        left: 0.88rem;
        top: 0.72rem;
        bottom: 0.72rem;
        width: 4px;
        border-radius: 999px;
        background: linear-gradient(180deg, #facc15 0%, #f59e0b 100%);
        box-shadow: 0 0 14px rgba(250, 204, 21, 0.28);
    }

    .section-header {
        position: relative;
        overflow: hidden;
        margin: 0.75rem 0 1rem;
        padding: 1rem 1.15rem;
        border-radius: 18px;
        background:
            radial-gradient(circle at top right, rgba(250, 204, 21, 0.16), rgba(250, 204, 21, 0) 36%),
            linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%);
        border: 1px solid rgba(250, 204, 21, 0.20);
        color: #f8fafc;
        font-size: 1.06rem;
        font-weight: 800;
        letter-spacing: 0.01em;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.12),
            0 16px 28px rgba(7, 20, 39, 0.16);
    }

    section[data-testid="stSidebar"] > div:first-child {
        background:
            radial-gradient(circle at top right, rgba(250, 204, 21, 0.12), rgba(250, 204, 21, 0) 34%),
            linear-gradient(180deg, #f7f9fd 0%, #eef3fa 60%, #f8f0e2 100%) !important;
    }

    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #17324a;
    }

    details[data-testid="stExpander"] {
        border: 1px solid var(--qa-surface-border) !important;
        border-radius: 18px !important;
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 10px 20px rgba(15, 23, 42, 0.06) !important;
        overflow: hidden;
    }

    details[data-testid="stExpander"] summary {
        background: transparent !important;
        padding: 0.2rem 0.3rem !important;
    }

    details[data-testid="stExpander"] > div[role="button"],
    details[data-testid="stExpander"] summary p {
        color: #17324a !important;
        font-weight: 700 !important;
    }

    details[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {
        border-top: 1px solid rgba(213, 220, 232, 0.86) !important;
        background: rgba(255, 255, 255, 0.36) !important;
    }

    /* 工具卡片网格布局 */
    .tools-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }

    .tool-card {
        background: linear-gradient(135deg, var(--qa-btn-primary-start) 0%, var(--qa-btn-primary-mid) 62%, var(--qa-btn-primary-end) 100%);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.12),
            0 12px 24px var(--qa-btn-primary-shadow);
        border: 1px solid var(--qa-btn-primary-border);
        transition: all 0.3s ease;
        cursor: pointer;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .tool-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 18px 32px rgba(7, 20, 39, 0.28);
        border-color: rgba(250, 204, 21, 0.30);
    }
    /* 选中的卡片样式 */
    .tool-card.selected {
        background: var(--qa-btn-primary-light);
        border-color: var(--qa-btn-primary-light-border);
        transform: scale(1.02);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.82),
            0 15px 35px rgba(250, 204, 21, 0.18);
    }

    .tool-card.selected .tool-icon {
        color: #7c2d12;
    }

    .tool-card.selected .tool-title {
        color: #17324a;
    }

    .tool-card.selected .tool-desc {
        color: #436176;
    }

    .tool-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #ffffff;
    }

    .tool-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }

    .tool-desc {
        color: rgba(255, 255, 255, 0.88);
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* 功能区域样式 */
    .section-card {
        background:
            var(--qa-surface-panel-soft);
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
        border: 1px solid var(--qa-surface-border);
    }

    .category-card {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel);
        border: 1px solid var(--qa-surface-border);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.84),
            0 8px 18px rgba(15, 23, 42, 0.06);
    }

    /* 按钮样式 */
    .stButton button,
    .stDownloadButton button {
        border-radius: 12px;
        font-weight: 700;
        padding: 0.75rem 1.2rem;
        transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease, background 0.24s ease;
        width: 100%;
        min-height: 44px;
    }

    .stButton button,
    .stDownloadButton button,
    .copy-btn,
    .card-button {
        text-shadow:
            0 1px 0 rgba(7, 20, 39, 0.38),
            0 0 10px rgba(255, 255, 255, 0.04);
    }

    .stButton button,
    .stDownloadButton button,
    .stButton button *,
    .stDownloadButton button *,
    .copy-btn,
    .copy-btn *,
    .card-button,
    .card-button * {
        color: #ffffff !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        opacity: 1 !important;
        font-weight: inherit !important;
    }

    .stButton button div[data-testid="stMarkdownContainer"],
    .stButton button div[data-testid="stMarkdownContainer"] p,
    .stButton button div[data-testid="stMarkdownContainer"] span,
    .stDownloadButton button div[data-testid="stMarkdownContainer"],
    .stDownloadButton button div[data-testid="stMarkdownContainer"] p,
    .stDownloadButton button div[data-testid="stMarkdownContainer"] span {
        color: #ffffff !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em !important;
        text-shadow: 0 1px 0 rgba(7, 20, 39, 0.44) !important;
        opacity: 1 !important;
    }

    .stDownloadButton button div[data-testid="stMarkdownContainer"],
    .stDownloadButton button div[data-testid="stMarkdownContainer"] p,
    .stDownloadButton button div[data-testid="stMarkdownContainer"] span {
        text-shadow: 0 1px 1px rgba(124, 45, 18, 0.54) !important;
    }

    .stButton button,
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, var(--qa-btn-primary-start) 0%, var(--qa-btn-primary-mid) 62%, var(--qa-btn-primary-end) 100%);
        color: white;
        border: 1px solid var(--qa-btn-primary-border);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.12),
            0 12px 22px var(--qa-btn-primary-shadow);
    }

    .stButton button:hover,
    .stButton button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.14),
            0 16px 28px rgba(7, 20, 39, 0.28);
    }

    .stButton button:active,
    .stButton button[kind="primary"]:active,
    .stButton button:focus-visible,
    .stButton button[kind="primary"]:focus-visible {
        background: var(--qa-btn-primary-light);
        color: #17324a;
        border-color: var(--qa-btn-primary-light-border);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.82),
            0 10px 22px rgba(250, 204, 21, 0.16);
    }

    .stButton button:active *,
    .stButton button[kind="primary"]:active *,
    .stButton button:focus-visible *,
    .stButton button[kind="primary"]:focus-visible * {
        color: #17324a !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
    }

    .stButton button:active div[data-testid="stMarkdownContainer"],
    .stButton button:active div[data-testid="stMarkdownContainer"] p,
    .stButton button:active div[data-testid="stMarkdownContainer"] span,
    .stButton button[kind="primary"]:active div[data-testid="stMarkdownContainer"],
    .stButton button[kind="primary"]:active div[data-testid="stMarkdownContainer"] p,
    .stButton button[kind="primary"]:active div[data-testid="stMarkdownContainer"] span,
    .stButton button:focus-visible div[data-testid="stMarkdownContainer"],
    .stButton button:focus-visible div[data-testid="stMarkdownContainer"] p,
    .stButton button:focus-visible div[data-testid="stMarkdownContainer"] span,
    .stButton button[kind="primary"]:focus-visible div[data-testid="stMarkdownContainer"],
    .stButton button[kind="primary"]:focus-visible div[data-testid="stMarkdownContainer"] p,
    .stButton button[kind="primary"]:focus-visible div[data-testid="stMarkdownContainer"] span {
        color: #17324a !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        text-shadow: none !important;
    }

    .stButton button[kind="secondary"] {
        background: var(--qa-btn-secondary-surface);
        color: #ffffff;
        border: 1px solid var(--qa-btn-secondary-border);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.12),
            0 10px 20px rgba(7, 20, 39, 0.22);
    }

    .stButton button[kind="secondary"]:hover {
        transform: translateY(-2px);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.14),
            0 14px 24px rgba(7, 20, 39, 0.24);
        border-color: rgba(250, 204, 21, 0.30);
    }

    .stButton button[kind="secondary"]:active,
    .stButton button[kind="secondary"]:focus-visible {
        background: var(--qa-btn-primary-light);
        color: #17324a;
        border-color: var(--qa-btn-primary-light-border);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.82),
            0 10px 22px rgba(250, 204, 21, 0.16);
    }

    .stButton button[kind="secondary"]:active *,
    .stButton button[kind="secondary"]:focus-visible * {
        color: #17324a !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
    }

    .stButton button[kind="secondary"]:active div[data-testid="stMarkdownContainer"],
    .stButton button[kind="secondary"]:active div[data-testid="stMarkdownContainer"] p,
    .stButton button[kind="secondary"]:active div[data-testid="stMarkdownContainer"] span,
    .stButton button[kind="secondary"]:focus-visible div[data-testid="stMarkdownContainer"],
    .stButton button[kind="secondary"]:focus-visible div[data-testid="stMarkdownContainer"] p,
    .stButton button[kind="secondary"]:focus-visible div[data-testid="stMarkdownContainer"] span {
        color: #17324a !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        text-shadow: none !important;
    }

    .stDownloadButton button,
    .stDownloadButton button[kind="primary"],
    .stDownloadButton button[kind="secondary"] {
        background: var(--qa-btn-download-surface);
        color: #ffffff;
        border: 1px solid var(--qa-btn-download-border);
        text-shadow:
            0 1px 1px rgba(124, 45, 18, 0.54),
            0 0 12px rgba(124, 45, 18, 0.16);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.12),
            0 12px 22px var(--qa-btn-download-shadow);
    }

    .stDownloadButton button:hover,
    .stDownloadButton button[kind="primary"]:hover,
    .stDownloadButton button[kind="secondary"]:hover {
        transform: translateY(-2px);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.14),
            0 16px 28px rgba(124, 45, 18, 0.28);
        border-color: rgba(251, 146, 60, 0.34);
    }

    .stDownloadButton button:active,
    .stDownloadButton button[kind="primary"]:active,
    .stDownloadButton button[kind="secondary"]:active,
    .stDownloadButton button:focus-visible,
    .stDownloadButton button[kind="primary"]:focus-visible,
    .stDownloadButton button[kind="secondary"]:focus-visible {
        background: var(--qa-btn-download-light);
        color: #7c2d12;
        border-color: var(--qa-btn-download-light-border);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.84),
            0 10px 22px rgba(251, 146, 60, 0.18);
    }

    .stDownloadButton button:active *,
    .stDownloadButton button[kind="primary"]:active *,
    .stDownloadButton button[kind="secondary"]:active *,
    .stDownloadButton button:focus-visible *,
    .stDownloadButton button[kind="primary"]:focus-visible *,
    .stDownloadButton button[kind="secondary"]:focus-visible * {
        color: #7c2d12 !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
    }

    .stDownloadButton button:active div[data-testid="stMarkdownContainer"],
    .stDownloadButton button:active div[data-testid="stMarkdownContainer"] p,
    .stDownloadButton button:active div[data-testid="stMarkdownContainer"] span,
    .stDownloadButton button[kind="primary"]:active div[data-testid="stMarkdownContainer"],
    .stDownloadButton button[kind="primary"]:active div[data-testid="stMarkdownContainer"] p,
    .stDownloadButton button[kind="primary"]:active div[data-testid="stMarkdownContainer"] span,
    .stDownloadButton button[kind="secondary"]:active div[data-testid="stMarkdownContainer"],
    .stDownloadButton button[kind="secondary"]:active div[data-testid="stMarkdownContainer"] p,
    .stDownloadButton button[kind="secondary"]:active div[data-testid="stMarkdownContainer"] span,
    .stDownloadButton button:focus-visible div[data-testid="stMarkdownContainer"],
    .stDownloadButton button:focus-visible div[data-testid="stMarkdownContainer"] p,
    .stDownloadButton button:focus-visible div[data-testid="stMarkdownContainer"] span,
    .stDownloadButton button[kind="primary"]:focus-visible div[data-testid="stMarkdownContainer"],
    .stDownloadButton button[kind="primary"]:focus-visible div[data-testid="stMarkdownContainer"] p,
    .stDownloadButton button[kind="primary"]:focus-visible div[data-testid="stMarkdownContainer"] span,
    .stDownloadButton button[kind="secondary"]:focus-visible div[data-testid="stMarkdownContainer"],
    .stDownloadButton button[kind="secondary"]:focus-visible div[data-testid="stMarkdownContainer"] p,
    .stDownloadButton button[kind="secondary"]:focus-visible div[data-testid="stMarkdownContainer"] span {
        color: #7c2d12 !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        text-shadow: none !important;
    }

    .stButton button:disabled,
    .stDownloadButton button:disabled {
        opacity: 0.56;
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
    }

    .copy-btn {
        background: linear-gradient(135deg, var(--qa-btn-primary-start) 0%, var(--qa-btn-primary-mid) 62%, var(--qa-btn-primary-end) 100%);
        color: white;
        border: 1px solid var(--qa-btn-primary-border);
        padding: 0.6rem 1.5rem;
        border-radius: 12px;
        font-weight: 700;
        transition: all 0.3s ease;
        margin: 5px;
        box-shadow: 0 12px 22px var(--qa-btn-primary-shadow);
    }

    .copy-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 16px 28px rgba(7, 20, 39, 0.28);
    }

    .copy-btn:active,
    .copy-btn:focus-visible {
        background: var(--qa-btn-primary-light);
        color: #17324a;
        border-color: var(--qa-btn-primary-light-border);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.82),
            0 10px 22px rgba(250, 204, 21, 0.16);
    }

    .copy-btn:active,
    .copy-btn:focus-visible,
    .copy-btn:active *,
    .copy-btn:focus-visible * {
        color: #17324a !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        text-shadow: none !important;
    }

    /* 结果框样式 */
    .result-box {
        background:
            var(--qa-surface-panel-soft);
        border: 2px dashed var(--qa-surface-border-strong);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
        max-height: 400px;
        overflow-y: auto;
        font-size: 0.9rem;
    }

    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel);
        padding: 0.5rem;
        margin-bottom: 0.95rem;
        border-radius: 14px;
        border: 1px solid var(--qa-surface-border);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.84),
            0 10px 18px rgba(15, 23, 42, 0.06);
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background: linear-gradient(135deg, var(--qa-btn-primary-start) 0%, var(--qa-btn-primary-mid) 62%, var(--qa-btn-primary-end) 100%);
        color: #ffffff;
        border: 1px solid var(--qa-btn-primary-border);
        border-radius: 10px;
        gap: 1rem;
        padding: 0 1.5rem;
        font-weight: 700;
        font-size: 0.96rem;
        letter-spacing: 0.01em;
        text-shadow:
            0 1px 1px rgba(7, 20, 39, 0.42),
            0 0 10px rgba(255, 255, 255, 0.04);
        transition: transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease, background 0.24s ease;
    }

    .stTabs [data-baseweb="tab"],
    .stTabs [data-baseweb="tab"] *,
    .stTabs [data-baseweb="tab"] div,
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span {
        color: #ffffff !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        opacity: 1 !important;
        font-weight: 800 !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        transform: translateY(-1px);
        border-color: rgba(250, 204, 21, 0.30);
        box-shadow: 0 8px 16px rgba(7, 20, 39, 0.16);
    }

    .stTabs [aria-selected="true"] {
        background: var(--qa-btn-primary-light) !important;
        border-color: var(--qa-btn-primary-light-border) !important;
        color: #17324a !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.82),
            0 12px 22px rgba(250, 204, 21, 0.14);
    }

    .stTabs [aria-selected="true"],
    .stTabs [aria-selected="true"] *,
    .stTabs [aria-selected="true"] div,
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] span {
        color: #17324a !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        text-shadow: none !important;
        opacity: 1 !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background: transparent !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 0.1rem;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="base-input"] > div,
    div[data-testid="stTextInputRootElement"] > div,
    div[data-testid="stNumberInputContainer"] > div,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stDateInputField"] > div {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        border: 1px solid var(--qa-surface-border) !important;
        border-radius: 14px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 8px 18px rgba(15, 23, 42, 0.06) !important;
        transition: border-color 0.24s ease, box-shadow 0.24s ease, transform 0.24s ease;
    }

    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="base-input"] > div:hover,
    div[data-testid="stTextInputRootElement"] > div:hover,
    div[data-testid="stNumberInputContainer"] > div:hover,
    div[data-testid="stTextArea"] textarea:hover,
    div[data-testid="stDateInputField"] > div:hover {
        border-color: var(--qa-surface-border-strong) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.92),
            0 12px 20px rgba(15, 23, 42, 0.10) !important;
    }

    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="base-input"] > div:focus-within,
    div[data-testid="stTextInputRootElement"] > div:focus-within,
    div[data-testid="stNumberInputContainer"] > div:focus-within,
    div[data-testid="stTextArea"] textarea:focus,
    div[data-testid="stDateInputField"] > div:focus-within {
        border-color: rgba(29, 78, 216, 0.42) !important;
        box-shadow:
            0 0 0 1px rgba(29, 78, 216, 0.18),
            0 14px 22px rgba(15, 23, 42, 0.10) !important;
        outline: none !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input,
    div[data-baseweb="base-input"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stNumberInputContainer"] input,
    div[data-testid="stDateInputField"] input {
        color: #17324a !important;
    }

    div[data-baseweb="select"] [data-baseweb="tag"] {
        background: linear-gradient(135deg, rgba(23, 50, 74, 0.10) 0%, rgba(29, 78, 216, 0.12) 100%) !important;
        border: 1px solid rgba(29, 78, 216, 0.18) !important;
        color: #17324a !important;
        border-radius: 999px !important;
        font-weight: 700;
    }

    div[data-baseweb="select"] svg,
    div[data-baseweb="base-input"] svg {
        fill: #476179 !important;
    }

    label[data-testid="stWidgetLabel"] p {
        color: #36506a !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em;
    }

    label[data-testid="stWidgetLabel"] {
        display: block;
        margin-bottom: 0.42rem !important;
    }

    div[data-testid="stTextInput"],
    div[data-testid="stNumberInput"],
    div[data-testid="stTextArea"],
    div[data-testid="stSelectbox"],
    div[data-testid="stMultiSelect"],
    div[data-testid="stDateInput"],
    div[data-testid="stTimeInput"],
    div[data-testid="stRadio"],
    div[data-testid="stCheckbox"],
    div[data-testid="stSlider"],
    div[data-testid="stToggle"],
    div[data-testid="stFileUploader"],
    div[data-testid="stColorPicker"] {
        margin-bottom: var(--qa-flow-space-md) !important;
    }

    div[data-testid="stHorizontalBlock"] {
        row-gap: var(--qa-flow-space-sm) !important;
        column-gap: var(--qa-flow-space-md) !important;
        align-items: flex-start !important;
    }

    div[data-testid="stForm"] {
        margin: var(--qa-flow-space-sm) 0 var(--qa-flow-space-lg) !important;
        padding: 1rem 1rem 0.42rem !important;
        border-radius: 20px !important;
        border: 1px solid rgba(213, 220, 232, 0.82) !important;
        background:
            var(--qa-surface-radial),
            rgba(255,255,255,0.38) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.72),
            0 12px 24px rgba(15, 23, 42, 0.06) !important;
    }

    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] {
        margin-top: 0.18rem !important;
        padding-top: 0.12rem !important;
    }

    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.7rem;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"],
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        border: 1px solid var(--qa-surface-border) !important;
        border-radius: 14px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 8px 18px rgba(15, 23, 42, 0.06) !important;
        transition: transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease, background 0.24s ease;
        padding: 0.45rem 0.75rem !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover,
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:hover {
        transform: translateY(-1px);
        border-color: var(--qa-surface-border-strong) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.92),
            0 12px 20px rgba(15, 23, 42, 0.10) !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] p,
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] p {
        color: #36506a !important;
        font-weight: 700 !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked),
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) {
        background: linear-gradient(135deg, var(--qa-btn-primary-start) 0%, var(--qa-btn-primary-mid) 62%, var(--qa-btn-primary-end) 100%) !important;
        border-color: var(--qa-btn-primary-border) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.12),
            0 12px 22px rgba(23, 50, 74, 0.20) !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) p {
        color: #ffffff !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"] svg,
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] svg {
        fill: #476179 !important;
        color: #476179 !important;
    }

    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) svg,
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }

    div[data-testid="stFileUploader"] section,
    div[data-testid="stFileUploaderDropzone"] {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        border: 1px dashed var(--qa-surface-border-strong) !important;
        border-radius: 18px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 10px 20px rgba(15, 23, 42, 0.08) !important;
        transition: transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease;
    }

    div[data-testid="stFileUploader"] section:hover,
    div[data-testid="stFileUploaderDropzone"]:hover {
        transform: translateY(-1px);
        border-color: rgba(29, 78, 216, 0.42) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.92),
            0 14px 24px rgba(15, 23, 42, 0.12) !important;
    }

    div[data-testid="stFileUploader"] small,
    div[data-testid="stFileUploader"] p,
    div[data-testid="stFileUploaderDropzoneInstructions"] small,
    div[data-testid="stFileUploaderDropzoneInstructions"] p {
        color: #476179 !important;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] button,
    div[data-testid="stFileUploader"] section button {
        border-radius: 12px !important;
    }

    div[data-testid="stTable"],
    div[data-testid="stDataFrame"] {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        border: 1px solid var(--qa-surface-border) !important;
        border-radius: 18px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 12px 24px rgba(15, 23, 42, 0.08) !important;
        overflow: hidden !important;
    }

    div[data-testid="stTable"]:hover,
    div[data-testid="stDataFrame"]:hover {
        border-color: var(--qa-surface-border-strong) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.92),
            0 16px 28px rgba(15, 23, 42, 0.10) !important;
        transition: border-color 0.24s ease, box-shadow 0.24s ease, transform 0.24s ease;
    }

    div[data-testid="stDataFrameResizable"] {
        border: 0 !important;
        border-radius: 18px !important;
        background:
            radial-gradient(circle at top right, rgba(250, 204, 21, 0.08), rgba(250, 204, 21, 0) 34%),
            linear-gradient(180deg, rgba(255,255,255,0.82) 0%, rgba(245, 239, 226, 0.48) 100%) !important;
        padding: 0.15rem !important;
    }

    div[data-testid="stDataFrameGlideDataEditor"] {
        border-radius: 16px !important;
        overflow: hidden !important;
        background: rgba(255,255,255,0.74) !important;
    }

    div[data-testid="stDataFrameGlideDataEditor"] * {
        color: #17324a !important;
    }

    table[data-testid="stTableStyledTable"] {
        width: 100%;
        border-collapse: separate !important;
        border-spacing: 0;
        background: rgba(255,255,255,0.72) !important;
        border-radius: 16px !important;
        overflow: hidden !important;
    }

    table[data-testid="stTableStyledTable"] thead tr {
        background: linear-gradient(135deg, rgba(7, 20, 39, 0.96) 0%, rgba(19, 41, 75, 0.94) 62%, rgba(34, 77, 121, 0.92) 100%) !important;
    }

    table[data-testid="stTableStyledTable"] thead th {
        color: #f8fafc !important;
        font-weight: 800 !important;
        border-bottom: 1px solid rgba(250, 204, 21, 0.18) !important;
        padding-top: 0.8rem !important;
        padding-bottom: 0.8rem !important;
    }

    table[data-testid="stTableStyledTable"] tbody tr:nth-child(odd) {
        background: rgba(255,255,255,0.76) !important;
    }

    table[data-testid="stTableStyledTable"] tbody tr:nth-child(even) {
        background: rgba(244, 239, 228, 0.88) !important;
    }

    table[data-testid="stTableStyledTable"] tbody tr:hover {
        background: rgba(255, 246, 213, 0.94) !important;
    }

    table[data-testid="stTableStyledTable"] tbody td {
        color: #17324a !important;
        border-top: 1px solid rgba(213, 220, 232, 0.78) !important;
    }

    div[data-testid="stDataFrameColumnMenu"],
    div[data-testid="stDataFrameColumnFormattingMenu"],
    div[data-testid="stDataFrameColumnVisibilityMenu"],
    div[data-testid="stDataFrameTooltipContent"] {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        color: #17324a !important;
        border: 1px solid var(--qa-surface-border) !important;
        border-radius: 16px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 14px 26px rgba(15, 23, 42, 0.12) !important;
        overflow: hidden !important;
    }

    div[data-testid="stDataFrameColumnMenu"] *,
    div[data-testid="stDataFrameColumnFormattingMenu"] *,
    div[data-testid="stDataFrameColumnVisibilityMenu"] *,
    div[data-testid="stDataFrameTooltipContent"] * {
        color: #17324a !important;
    }

    div[data-testid="stDataFrameColumnMenu"] [role="menuitem"],
    div[data-testid="stDataFrameColumnFormattingMenu"] [role="menuitem"] {
        transition: background 0.24s ease, color 0.24s ease;
    }

    div[data-testid="stDataFrameColumnMenu"] [role="menuitem"]:hover,
    div[data-testid="stDataFrameColumnFormattingMenu"] [role="menuitem"]:hover {
        background: rgba(255, 246, 213, 0.86) !important;
    }

    .stDataFrameGlideDataEditor .gdg-search-bar {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        border: 1px solid var(--qa-surface-border) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 12px 22px rgba(15, 23, 42, 0.08) !important;
    }

    .stDataFrameGlideDataEditor .gdg-search-bar input,
    .stDataFrameGlideDataEditor .gdg-search-bar button,
    .stDataFrameGlideDataEditor .gdg-search-bar .gdg-search-status {
        color: #17324a !important;
    }

    div[data-testid="stPlotlyChart"],
    div[data-testid="stVegaLiteChart"],
    div[data-testid="stArrowVegaLiteChart"],
    div[data-testid="stDeckGlJsonChart"],
    div.element-container:has(.js-plotly-plot),
    div.element-container:has(.vega-embed) {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        border: 1px solid var(--qa-surface-border) !important;
        border-radius: 20px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 14px 28px rgba(15, 23, 42, 0.08) !important;
        padding: 0.7rem 0.8rem 0.55rem !important;
        overflow: hidden !important;
    }

    div[data-testid="stPlotlyChart"]:hover,
    div[data-testid="stVegaLiteChart"]:hover,
    div[data-testid="stArrowVegaLiteChart"]:hover,
    div[data-testid="stDeckGlJsonChart"]:hover,
    div.element-container:has(.js-plotly-plot):hover,
    div.element-container:has(.vega-embed):hover {
        border-color: var(--qa-surface-border-strong) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.92),
            0 18px 30px rgba(15, 23, 42, 0.10) !important;
        transition: border-color 0.24s ease, box-shadow 0.24s ease;
    }

    div[data-testid="stPlotlyChart"] .js-plotly-plot,
    div.element-container:has(.js-plotly-plot) .js-plotly-plot,
    div[data-testid="stVegaLiteChart"] .vega-embed,
    div[data-testid="stArrowVegaLiteChart"] .vega-embed,
    div.element-container:has(.vega-embed) .vega-embed {
        background: transparent !important;
    }

    .js-plotly-plot .modebar {
        background: rgba(247, 239, 223, 0.84) !important;
        border: 1px solid rgba(199, 164, 79, 0.26) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 16px rgba(15, 23, 42, 0.08) !important;
    }

    .js-plotly-plot .modebar-btn svg,
    .js-plotly-plot .modebar-btn path {
        fill: #17324a !important;
    }

    .js-plotly-plot .modebar-btn:hover {
        background: rgba(255, 246, 213, 0.82) !important;
    }

    div[data-testid="stMarkdownContainer"] h3 {
        position: relative;
        margin: 1.35rem 0 0.8rem !important;
        padding: 0.1rem 0 0.55rem 1rem !important;
        color: #17324a !important;
        font-size: 1.18rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em !important;
        border-bottom: 1px solid rgba(199, 164, 79, 0.20) !important;
    }

    div[data-testid="stMarkdownContainer"] h3::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0.18rem;
        bottom: 0.62rem;
        width: 4px;
        border-radius: 999px;
        background: linear-gradient(180deg, #facc15 0%, #f59e0b 100%);
        box-shadow: 0 0 12px rgba(250, 204, 21, 0.24);
    }

    div[data-testid="stMarkdownContainer"] h4 {
        margin: 1.15rem 0 0.65rem !important;
        color: #17324a !important;
        font-size: 1.02rem !important;
        font-weight: 760 !important;
        letter-spacing: 0.01em !important;
    }

    div[data-testid="stMarkdownContainer"] h5,
    div[data-testid="stMarkdownContainer"] h6 {
        margin: 1rem 0 0.55rem !important;
        color: #34506b !important;
        font-size: 0.92rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
        text-transform: uppercase;
    }

    div[data-testid="stMarkdownContainer"] {
        line-height: 1.72;
    }

    div[data-testid="stMarkdownContainer"] > :first-child {
        margin-top: 0 !important;
    }

    div[data-testid="stMarkdownContainer"] > :last-child {
        margin-bottom: 0 !important;
    }

    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] ul,
    div[data-testid="stMarkdownContainer"] ol {
        margin-top: var(--qa-flow-space-xs) !important;
        margin-bottom: var(--qa-flow-space-sm) !important;
        color: #34506b !important;
        line-height: 1.72 !important;
    }

    div[data-testid="stMarkdownContainer"] ul,
    div[data-testid="stMarkdownContainer"] ol {
        padding-left: 1.2rem !important;
    }

    div[data-testid="stMarkdownContainer"] li {
        margin: 0.24rem 0 !important;
        color: #34506b !important;
        line-height: 1.68 !important;
    }

    div[data-testid="stMarkdownContainer"] h3 + p,
    div[data-testid="stMarkdownContainer"] h4 + p,
    div[data-testid="stMarkdownContainer"] h5 + p,
    div[data-testid="stMarkdownContainer"] h6 + p,
    div[data-testid="stMarkdownContainer"] h3 + ul,
    div[data-testid="stMarkdownContainer"] h4 + ul,
    div[data-testid="stMarkdownContainer"] h3 + ol,
    div[data-testid="stMarkdownContainer"] h4 + ol {
        margin-top: 0.32rem !important;
    }

    div[data-testid="stMarkdownContainer"] p + p,
    div[data-testid="stMarkdownContainer"] ul + p,
    div[data-testid="stMarkdownContainer"] ol + p,
    div[data-testid="stMarkdownContainer"] p + ul,
    div[data-testid="stMarkdownContainer"] p + ol,
    div[data-testid="stMarkdownContainer"] blockquote + p,
    div[data-testid="stMarkdownContainer"] pre + p,
    div[data-testid="stMarkdownContainer"] table + p {
        margin-top: var(--qa-flow-space-md) !important;
    }

    div[data-testid="stMarkdownContainer"] blockquote {
        margin: 1rem 0 !important;
        padding: 0.9rem 1rem 0.9rem 1.1rem !important;
        background:
            radial-gradient(circle at top right, rgba(250, 204, 21, 0.10), rgba(250, 204, 21, 0) 34%),
            linear-gradient(145deg, rgba(247,249,253,0.96) 0%, rgba(238,243,250,0.96) 56%, rgba(247,239,223,0.96) 100%) !important;
        border: 1px solid rgba(213, 220, 232, 0.84) !important;
        border-left: 4px solid #f59e0b !important;
        border-radius: 16px !important;
        color: #476179 !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 10px 20px rgba(15, 23, 42, 0.08) !important;
    }

    div[data-testid="stMarkdownContainer"] blockquote p,
    div[data-testid="stMarkdownContainer"] blockquote li,
    div[data-testid="stMarkdownContainer"] blockquote span {
        color: #476179 !important;
    }

    div[data-testid="stMarkdownContainer"] :not(pre) > code {
        background: linear-gradient(145deg, rgba(7, 20, 39, 0.08) 0%, rgba(34, 77, 121, 0.10) 100%) !important;
        color: #17324a !important;
        border: 1px solid rgba(199, 164, 79, 0.18) !important;
        border-radius: 10px !important;
        padding: 0.16rem 0.42rem !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.76);
    }

    div[data-testid="stMarkdownContainer"] pre,
    div[data-testid="stCode"] pre,
    div.stCode pre {
        background:
            radial-gradient(circle at top right, rgba(250, 204, 21, 0.08), rgba(250, 204, 21, 0) 32%),
            linear-gradient(160deg, rgba(7, 20, 39, 0.98) 0%, rgba(19, 41, 75, 0.98) 62%, rgba(9, 17, 31, 0.98) 100%) !important;
        border: 1px solid rgba(250, 204, 21, 0.16) !important;
        border-radius: 18px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.08),
            0 16px 28px rgba(7, 20, 39, 0.18) !important;
        color: #e8eef8 !important;
    }

    div[data-testid="stMarkdownContainer"] pre code,
    div[data-testid="stCode"] pre code,
    div.stCode pre code {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: inherit !important;
        padding: 0 !important;
    }

    div[data-testid="stCode"],
    div.stCode {
        border-radius: 18px !important;
        background: transparent !important;
    }

    div[data-testid="stCode"] button[data-testid="stCodeCopyButton"],
    div.stCode button[data-testid="stCodeCopyButton"] {
        background:
            linear-gradient(135deg, rgba(247,249,253,0.90) 0%, rgba(247,239,223,0.92) 100%) !important;
        border: 1px solid rgba(199, 164, 79, 0.26) !important;
        border-radius: 12px !important;
        color: #17324a !important;
        box-shadow: 0 8px 16px rgba(7, 20, 39, 0.12) !important;
    }

    div[data-testid="stCode"] button[data-testid="stCodeCopyButton"]:hover,
    div.stCode button[data-testid="stCodeCopyButton"]:hover {
        background: rgba(255, 246, 213, 0.92) !important;
    }

    div[data-testid="stCode"] button[data-testid="stCodeCopyButton"] svg,
    div[data-testid="stCode"] button[data-testid="stCodeCopyButton"] path,
    div.stCode button[data-testid="stCodeCopyButton"] svg,
    div.stCode button[data-testid="stCodeCopyButton"] path {
        fill: #17324a !important;
        color: #17324a !important;
    }

    div[data-testid="stMarkdownContainer"] pre::-webkit-scrollbar,
    div[data-testid="stCode"] pre::-webkit-scrollbar,
    div.stCode pre::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    div[data-testid="stMarkdownContainer"] pre::-webkit-scrollbar-thumb,
    div[data-testid="stCode"] pre::-webkit-scrollbar-thumb,
    div.stCode pre::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, rgba(250, 204, 21, 0.52) 0%, rgba(34, 77, 121, 0.56) 100%);
        border-radius: 999px;
        border: 2px solid rgba(7, 20, 39, 0.78);
    }

    div[data-testid="stMarkdownContainer"] pre::-webkit-scrollbar-track,
    div[data-testid="stCode"] pre::-webkit-scrollbar-track,
    div.stCode pre::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 999px;
    }

    div[data-testid="stMarkdownContainer"] table {
        width: 100%;
        border-collapse: separate !important;
        border-spacing: 0;
        margin: 1rem 0 1.1rem !important;
        background:
            var(--qa-surface-radial),
            rgba(255,255,255,0.82) !important;
        border: 1px solid var(--qa-surface-border) !important;
        border-radius: 18px !important;
        overflow: hidden !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 12px 24px rgba(15, 23, 42, 0.08) !important;
    }

    div[data-testid="stMarkdownContainer"] table thead tr {
        background: linear-gradient(135deg, rgba(7, 20, 39, 0.96) 0%, rgba(19, 41, 75, 0.94) 62%, rgba(34, 77, 121, 0.92) 100%) !important;
    }

    div[data-testid="stMarkdownContainer"] table thead th {
        color: #f8fafc !important;
        font-weight: 800 !important;
        border-bottom: 1px solid rgba(250, 204, 21, 0.16) !important;
    }

    div[data-testid="stMarkdownContainer"] table th,
    div[data-testid="stMarkdownContainer"] table td {
        padding: 0.78rem 0.9rem !important;
        border: 0 !important;
    }

    div[data-testid="stMarkdownContainer"] table tbody tr:nth-child(odd) {
        background: rgba(255,255,255,0.76) !important;
    }

    div[data-testid="stMarkdownContainer"] table tbody tr:nth-child(even) {
        background: rgba(244, 239, 228, 0.88) !important;
    }

    div[data-testid="stMarkdownContainer"] table tbody tr:hover {
        background: rgba(255, 246, 213, 0.94) !important;
    }

    div[data-testid="stMarkdownContainer"] table tbody td {
        color: #17324a !important;
        border-top: 1px solid rgba(213, 220, 232, 0.76) !important;
    }

    hr,
    div[data-testid="stMarkdownContainer"] hr,
    section[data-testid="stSidebar"] hr {
        border: 0 !important;
        height: 1px !important;
        margin: 1.1rem 0 1.15rem !important;
        background:
            linear-gradient(
                90deg,
                rgba(34, 77, 121, 0.04) 0%,
                rgba(199, 164, 79, 0.78) 18%,
                rgba(34, 77, 121, 0.78) 50%,
                rgba(199, 164, 79, 0.78) 82%,
                rgba(34, 77, 121, 0.04) 100%
            ) !important;
        box-shadow: 0 0 12px rgba(199, 164, 79, 0.10);
    }

    div[data-testid="stCaptionContainer"],
    div[data-testid="stCaptionContainer"] p,
    div[data-testid="stCaptionContainer"] span,
    div.stCaption,
    div.stCaption p,
    div.stCaption span,
    div[data-testid="stImageCaption"],
    div[data-testid="stImageCaption"] p,
    div[data-testid="stImageCaption"] span {
        color: #476179 !important;
        font-size: 0.84rem !important;
        line-height: 1.62 !important;
        letter-spacing: 0.01em !important;
    }

    /* 侧边栏样式 */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }

    /* 指标卡片 */
    .metric-card {
        background: var(--qa-surface-panel-soft);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
        text-align: center;
        border-left: 4px solid #f59e0b;
    }

    div[data-testid="stMetric"] {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft);
        border: 1px solid var(--qa-surface-border);
        border-left: 4px solid #f59e0b;
        border-radius: 16px;
        padding: 0.9rem 1rem;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.84),
            0 10px 20px rgba(15, 23, 42, 0.08);
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 14px 24px rgba(15, 23, 42, 0.12);
        transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
        border-color: var(--qa-surface-border-strong);
    }

    div[data-testid="stMetricLabel"] p {
        color: #476179 !important;
        font-size: 0.88rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em;
    }

    div[data-testid="stMetricValue"] {
        color: #17324a !important;
    }

    div[data-testid="stMetricValue"] > div,
    div[data-testid="stMetricValue"] p {
        color: #17324a !important;
        font-weight: 800 !important;
    }

    div[data-testid="stMetricDelta"] {
        color: #b45309 !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricDelta"] svg {
        fill: currentColor !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) div[data-testid="stAlertContainer"] {
        background:
            linear-gradient(145deg, rgba(255, 247, 230, 0.98) 0%, rgba(250, 238, 206, 0.98) 54%, rgba(247, 240, 226, 0.98) 100%) !important;
        border: 1px solid rgba(251, 146, 60, 0.24) !important;
        border-left: 4px solid #f59e0b !important;
        border-radius: 16px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.86),
            0 12px 24px rgba(124, 45, 18, 0.12) !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) div[data-testid="stMarkdownContainer"],
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) div[data-testid="stMarkdownContainer"] span {
        color: #9a3412 !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) [data-testid="stAlertDynamicIcon"] svg,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) [data-testid="stAlertDynamicIcon"] path {
        fill: #b45309 !important;
        color: #b45309 !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) div[data-testid="stAlertContainer"] {
        background:
            linear-gradient(145deg, rgba(238, 244, 255, 0.98) 0%, rgba(230, 237, 247, 0.98) 58%, rgba(243, 246, 251, 0.98) 100%) !important;
        border: 1px solid rgba(34, 77, 121, 0.20) !important;
        border-left: 4px solid #224d79 !important;
        border-radius: 16px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 12px 24px rgba(7, 20, 39, 0.10) !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) div[data-testid="stMarkdownContainer"],
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) div[data-testid="stMarkdownContainer"] span {
        color: #17324a !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) [data-testid="stAlertDynamicIcon"] svg,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) [data-testid="stAlertDynamicIcon"] path {
        fill: #224d79 !important;
        color: #224d79 !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) div[data-testid="stAlertContainer"] {
        background:
            linear-gradient(145deg, rgba(255, 248, 229, 0.98) 0%, rgba(251, 239, 200, 0.98) 56%, rgba(248, 242, 223, 0.98) 100%) !important;
        border: 1px solid rgba(217, 119, 6, 0.22) !important;
        border-left: 4px solid #d97706 !important;
        border-radius: 16px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 12px 24px rgba(146, 64, 14, 0.10) !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) div[data-testid="stMarkdownContainer"],
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) div[data-testid="stMarkdownContainer"] span {
        color: #92400e !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) [data-testid="stAlertDynamicIcon"] svg,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentWarning"]) [data-testid="stAlertDynamicIcon"] path {
        fill: #b45309 !important;
        color: #b45309 !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) div[data-testid="stAlertContainer"] {
        background:
            linear-gradient(145deg, rgba(255, 241, 238, 0.98) 0%, rgba(253, 230, 223, 0.98) 56%, rgba(248, 236, 232, 0.98) 100%) !important;
        border: 1px solid rgba(220, 38, 38, 0.18) !important;
        border-left: 4px solid #dc2626 !important;
        border-radius: 16px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 12px 24px rgba(153, 27, 27, 0.10) !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) div[data-testid="stMarkdownContainer"],
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) div[data-testid="stMarkdownContainer"] span {
        color: #991b1b !important;
    }

    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) [data-testid="stAlertDynamicIcon"] svg,
    div[data-testid="stAlert"]:has(div[data-testid="stAlertContentError"]) [data-testid="stAlertDynamicIcon"] path {
        fill: #b91c1c !important;
        color: #b91c1c !important;
    }

    div[data-testid="stPopoverBody"],
    div[data-baseweb="popover"] {
        background:
            var(--qa-surface-radial),
            var(--qa-surface-panel-soft) !important;
        border: 1px solid var(--qa-surface-border) !important;
        border-radius: 24px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.88),
            0 20px 40px rgba(15, 23, 42, 0.14) !important;
        color: #17324a !important;
    }

    div[data-testid="stPopoverBody"] *,
    div[data-baseweb="popover"] * {
        color: inherit !important;
    }

    div[data-testid="stPopoverBody"] hr,
    div[data-baseweb="popover"] hr {
        border-color: rgba(213, 220, 232, 0.72) !important;
    }

    div[data-baseweb="popover"] ul[role="listbox"],
    div[data-baseweb="popover"] div[role="listbox"],
    div[data-baseweb="popover"] div[role="menu"] {
        background: transparent !important;
        padding: 0.3rem !important;
    }

    div[data-baseweb="popover"] li[role="option"],
    div[data-baseweb="popover"] div[role="option"],
    div[data-baseweb="popover"] div[role="menuitem"] {
        color: #17324a !important;
        border-radius: 14px !important;
        border: 1px solid transparent !important;
        transition: background 0.22s ease, border-color 0.22s ease, transform 0.22s ease;
    }

    div[data-baseweb="popover"] li[role="option"]:hover,
    div[data-baseweb="popover"] div[role="option"]:hover,
    div[data-baseweb="popover"] div[role="menuitem"]:hover {
        background: rgba(255, 246, 213, 0.86) !important;
        border-color: rgba(199, 164, 79, 0.22) !important;
    }

    div[data-baseweb="popover"] li[role="option"][aria-selected="true"],
    div[data-baseweb="popover"] div[role="option"][aria-selected="true"],
    div[data-baseweb="popover"] div[role="menuitem"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(7, 20, 39, 0.96) 0%, rgba(19, 41, 75, 0.94) 62%, rgba(34, 77, 121, 0.92) 100%) !important;
        color: #f8fafc !important;
        border-color: rgba(250, 204, 21, 0.18) !important;
        box-shadow: 0 10px 18px rgba(7, 20, 39, 0.12) !important;
    }

    div[data-baseweb="popover"] li[role="option"][aria-selected="true"] *,
    div[data-baseweb="popover"] div[role="option"][aria-selected="true"] *,
    div[data-baseweb="popover"] div[role="menuitem"][aria-selected="true"] * {
        color: #f8fafc !important;
    }

    div[data-baseweb="popover"] div[role="tooltip"] {
        max-width: 320px !important;
        color: #17324a !important;
        line-height: 1.65 !important;
    }

    div[data-baseweb="popover"] div[role="tooltip"] p,
    div[data-baseweb="popover"] div[role="tooltip"] span,
    div[data-baseweb="popover"] div[role="tooltip"] li {
        color: #17324a !important;
    }

    div[data-baseweb="popover"]::-webkit-scrollbar,
    div[data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar,
    div[data-baseweb="popover"] [role="menu"]::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    div[data-baseweb="popover"]::-webkit-scrollbar-thumb,
    div[data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar-thumb,
    div[data-baseweb="popover"] [role="menu"]::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, rgba(34, 77, 121, 0.58) 0%, rgba(180, 83, 9, 0.56) 100%);
        border-radius: 999px;
        border: 2px solid rgba(247, 249, 253, 0.78);
    }

    div[data-baseweb="popover"]::-webkit-scrollbar-track,
    div[data-baseweb="popover"] [role="listbox"]::-webkit-scrollbar-track,
    div[data-baseweb="popover"] [role="menu"]::-webkit-scrollbar-track {
        background: rgba(238, 243, 250, 0.72);
        border-radius: 999px;
    }

    div[data-testid="stDialog"] {
        background: rgba(7, 20, 39, 0.38) !important;
        backdrop-filter: blur(10px);
    }

    div[data-testid="stDialog"] [role="dialog"] {
        background:
            radial-gradient(circle at top right, rgba(250, 204, 21, 0.12), rgba(250, 204, 21, 0) 34%),
            linear-gradient(145deg, rgba(247,249,253,0.99) 0%, rgba(238,243,250,0.99) 56%, rgba(247,239,223,0.99) 100%) !important;
        border: 1px solid rgba(199, 164, 79, 0.38) !important;
        border-radius: 28px !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.92),
            0 28px 60px rgba(7, 20, 39, 0.22) !important;
        color: #17324a !important;
    }

    div[data-testid="stDialog"] [role="dialog"] * {
        color: inherit;
    }

    div[data-testid="stDialog"] [role="dialog"] h1,
    div[data-testid="stDialog"] [role="dialog"] h2,
    div[data-testid="stDialog"] [role="dialog"] h3,
    div[data-testid="stDialog"] [role="dialog"] p,
    div[data-testid="stDialog"] [role="dialog"] label,
    div[data-testid="stDialog"] [role="dialog"] span,
    div[data-testid="stDialog"] [role="dialog"] li {
        color: #17324a !important;
    }

    div[data-testid="stDialog"] button[aria-label="Close"],
    div[data-testid="stDialog"] button[aria-label="关闭"] {
        color: #17324a !important;
    }

    div[data-testid="stDialog"] button[aria-label="Close"]:hover,
    div[data-testid="stDialog"] button[aria-label="关闭"]:hover {
        background: rgba(255, 246, 213, 0.82) !important;
    }

    div[data-testid="stDialog"] button[aria-label="Close"] svg,
    div[data-testid="stDialog"] button[aria-label="Close"] path,
    div[data-testid="stDialog"] button[aria-label="关闭"] svg,
    div[data-testid="stDialog"] button[aria-label="关闭"] path {
        fill: #17324a !important;
        color: #17324a !important;
    }

    /* 响应式调整 */
    @media (max-width: 768px) {
        .tools-grid {
            grid-template-columns: 1fr;
        }

        .main-header {
            font-size: 2rem;
        }

        .qa-app-hero {
            padding: 2rem 1.2rem 2.1rem;
            margin: -1rem -1rem 1.4rem -1rem;
            border-radius: 0 0 22px 22px;
        }

        .qa-app-hero__grid {
            grid-template-columns: 1fr;
            gap: 1.4rem;
        }

        .qa-app-hero__stage {
            min-height: 220px;
        }

        .qa-app-hero__stage-shell {
            width: min(280px, 100%);
        }

        .qa-app-hero__node {
            font-size: 0.74rem;
            padding: 0.42rem 0.7rem;
        }

        .qa-app-hero__curtain {
            width: 22%;
        }
    }

    /* 卡片按钮样式 */
    .card-button {
        background: linear-gradient(135deg, var(--qa-btn-primary-start) 0%, var(--qa-btn-primary-mid) 62%, var(--qa-btn-primary-end) 100%) !important;
        color: #ffffff !important;
        border: 1px solid var(--qa-btn-primary-border) !important;
        padding: 1.5rem !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        height: auto !important;
        min-height: 180px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.12),
            0 12px 24px rgba(7, 20, 39, 0.24) !important;
    }

    .card-button:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 18px 30px rgba(7, 20, 39, 0.28) !important;
        border-color: rgba(250, 204, 21, 0.30) !important;
        background: linear-gradient(135deg, var(--qa-btn-primary-start) 0%, var(--qa-btn-primary-mid) 62%, var(--qa-btn-primary-end) 100%) !important;
        color: #ffffff !important;
    }

    /* 选中状态的卡片按钮 */
    .selected-card-button {
        background: var(--qa-btn-primary-light) !important;
        color: #17324a !important;
        border: 1px solid var(--qa-btn-primary-light-border) !important;
        transform: scale(1.02) !important;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.82),
            0 16px 28px rgba(250, 204, 21, 0.18) !important;
    }

    .selected-card-button,
    .selected-card-button * {
        color: #17324a !important;
        fill: currentColor !important;
        stroke: currentColor !important;
        -webkit-text-fill-color: currentColor !important;
        text-shadow: none !important;
    }

    .selected-card-button:hover {
        background: var(--qa-btn-primary-light) !important;
        color: #17324a !important;
        transform: translateY(-4px) scale(1.02) !important;
        box-shadow: 0 20px 34px rgba(250, 204, 21, 0.20) !important;
    }

    .tool-picker-card {
        background: linear-gradient(135deg, var(--qa-btn-primary-start) 0%, var(--qa-btn-primary-mid) 62%, var(--qa-btn-primary-end) 100%);
        border-radius: 16px;
        border: 1px solid var(--qa-btn-primary-border);
        box-shadow:
            0 14px 30px rgba(7, 20, 39, 0.24),
            inset 0 1px 0 rgba(255,255,255,0.12);
        padding: 1.25rem;
        min-height: 188px;
        margin-bottom: 0;
        transition: all 0.25s ease;
        cursor: pointer;
    }

    .tool-picker-card.selected {
        background: var(--qa-btn-primary-light);
        border-color: var(--qa-btn-primary-light-border);
        box-shadow:
            inset 1px 1px 0 rgba(255,255,255,0.82),
            0 16px 28px rgba(250, 204, 21, 0.18);
        transform: translateY(-1px);
    }

    .tool-picker-linklike {
        display: block;
        color: inherit !important;
        text-decoration: none !important;
        cursor: pointer;
        user-select: none;
        -webkit-tap-highlight-color: transparent;
    }

    .tool-picker-linklike:hover,
    .tool-picker-linklike:focus,
    .tool-picker-linklike:active,
    .tool-picker-linklike:visited {
        color: inherit !important;
        text-decoration: none !important;
        outline: none !important;
    }

    .tool-picker-linklike:hover .tool-picker-card,
    .tool-picker-linklike:focus .tool-picker-card {
        transform: translateY(-4px);
        box-shadow:
            0 18px 32px rgba(7, 20, 39, 0.28),
            inset 0 1px 0 rgba(255,255,255,0.14);
    }

    .tool-picker-linklike:focus-visible .tool-picker-card {
        transform: translateY(-4px);
        border-color: rgba(250, 204, 21, 0.42);
        box-shadow:
            0 0 0 3px rgba(250, 204, 21, 0.16),
            0 18px 32px rgba(7, 20, 39, 0.28),
            inset 0 1px 0 rgba(255,255,255,0.14);
    }

    .tool-picker-linklike:hover .tool-picker-card.selected,
    .tool-picker-linklike:focus .tool-picker-card.selected {
        background: var(--qa-btn-primary-light);
        border-color: var(--qa-btn-primary-light-border);
        box-shadow:
            inset 1px 1px 0 rgba(255,255,255,0.82),
            0 20px 34px rgba(250, 204, 21, 0.20);
    }

    .tool-picker-linklike:focus-visible .tool-picker-card.selected {
        background: var(--qa-btn-primary-light);
        border-color: rgba(250, 204, 21, 0.46);
        box-shadow:
            0 0 0 3px rgba(250, 204, 21, 0.16),
            inset 1px 1px 0 rgba(255,255,255,0.82),
            0 20px 34px rgba(250, 204, 21, 0.20);
    }

    .tool-picker-linklike:active .tool-picker-card {
        transform: translateY(-1px) scale(0.992);
        box-shadow:
            0 10px 20px rgba(7, 20, 39, 0.20),
            inset 0 1px 0 rgba(255,255,255,0.12);
    }

    .tool-picker-linklike:active .tool-picker-card.selected {
        background: var(--qa-btn-primary-light);
        border-color: var(--qa-btn-primary-light-border);
        box-shadow:
            inset 1px 1px 0 rgba(255,255,255,0.82),
            0 12px 22px rgba(250, 204, 21, 0.16);
    }

    .tool-picker-linklike:hover + .tool-picker-status,
    .tool-picker-linklike:focus-visible + .tool-picker-status {
        color: #17324a;
    }

    div[data-testid="stElementContainer"][class*="st-key-tool_picker_card_trigger_"] {
        margin: 0 !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
    }

    div[data-testid="stElementContainer"][class*="st-key-tool_picker_card_trigger_"] .stButton {
        height: 0 !important;
        min-height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    div[data-testid="stElementContainer"][class*="st-key-tool_picker_card_trigger_"] .stButton button {
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        margin: 0 !important;
        opacity: 0 !important;
        box-shadow: none !important;
    }

    .tool-picker-icon {
        font-size: 2rem;
        line-height: 1;
        margin-bottom: 0.75rem;
    }

    .tool-picker-title {
        font-size: 1.12rem;
        font-weight: 700;
        color: #ffffff;
        text-shadow:
            0 1px 0 rgba(7, 20, 39, 0.42),
            0 0 10px rgba(255, 255, 255, 0.04);
        margin-bottom: 0.5rem;
    }

    .tool-picker-desc {
        color: rgba(255, 255, 255, 0.96);
        font-size: 0.93rem;
        line-height: 1.55;
        min-height: 3.2rem;
        font-weight: 600;
        text-shadow: 0 1px 0 rgba(7, 20, 39, 0.32);
    }

    .tool-picker-card.selected .tool-picker-title {
        color: #17324a;
        text-shadow: none;
    }

    .tool-picker-card.selected .tool-picker-desc {
        color: #436176;
        text-shadow: none;
    }

    .tool-picker-status {
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 0.45rem;
        margin-bottom: 0.75rem;
        text-align: center;
        font-weight: 600;
    }

    .tool-picker-status.selected {
        color: #17324a;
    }
</style>
"""
# 顶部标题区域
HEADLINE_STYLES = """
<div class="qa-app-hero">
    <div class="qa-app-hero__curtain qa-app-hero__curtain--left"></div>
    <div class="qa-app-hero__curtain qa-app-hero__curtain--right"></div>
    <div class="qa-app-hero__glow qa-app-hero__glow--amber"></div>
    <div class="qa-app-hero__glow qa-app-hero__glow--teal"></div>
    <div class="qa-app-hero__grid">
        <div class="qa-app-hero__copy">
            <div class="qa-app-hero__kicker">QA TOOLKIT</div>
            <h1 class="qa-app-hero__title">
                <span class="qa-app-hero__title-main">测试工程师</span>
                <span class="qa-app-hero__title-focus">常用工具集</span>
            </h1>
            <p class="qa-app-hero__desc">
                围绕测试数据、日志、正则、文本、接口与质量分析的工程化工具台，
                把高频测试动作收进一个统一入口。
            </p>
            <div class="qa-app-hero__chip-row">
                <span class="qa-app-hero__chip">正则与文本</span>
                <span class="qa-app-hero__chip">日志与 JSON</span>
                <span class="qa-app-hero__chip">接口与分析</span>
            </div>
            <div class="qa-app-hero__meta-row">
                <span class="qa-app-hero__meta">一站式入口</span>
                <span class="qa-app-hero__meta">工程化提效</span>
                <span class="qa-app-hero__meta">面向测试实战</span>
            </div>
            <div class="qa-app-hero__footnote">
                从日常排查到专项分析，常用工具和辅助流程都集中在这里。
            </div>
        </div>
        <div class="qa-app-hero__stage">
            <div class="qa-app-hero__stage-shell">
                <div class="qa-app-hero__ring"></div>
                <div class="qa-app-hero__scan"></div>
                <a class="qa-app-hero__node qa-app-hero__node--1" href="?hero_tool=regex#tool-content-anchor">Regex</a>
                <a class="qa-app-hero__node qa-app-hero__node--2" href="?hero_tool=json#tool-content-anchor">JSON</a>
                <a class="qa-app-hero__node qa-app-hero__node--3" href="?hero_tool=logs#tool-content-anchor">Logs</a>
                <a class="qa-app-hero__node qa-app-hero__node--4" href="?hero_tool=api#tool-content-anchor">API</a>
                <div class="qa-app-hero__core">
                    <div class="qa-app-hero__core-inner">
                        <div class="qa-app-hero__core-label">TOOL HUB</div>
                        <div class="qa-app-hero__core-title">QA</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
"""
PRESET_SIZES = {
    "社交媒体头像 (200×200)": (200, 200),
    "社交媒体帖子 (1080×1080)": (1080, 1080),
    "手机壁纸 (1080×1920)": (1080, 1920),
    "电脑壁纸 (1920×1080)": (1920, 1080),
    "微信头像 (640×640)": (640, 640),
}

# 在文件开头添加预定义模式和语言模板
PREDEFINED_PATTERNS = {
    "中文字符": r"[\u4e00-\u9fa5]",
    "双字节字符": r"[^\x00-\xff]",
    "空白行": r"\n\s*\r",
    "Email地址": r"\w[-\w.+]*@([A-Za-z0-9][-A-Za-z0-9]+\.)+[A-Za-z]{2,14}",
    "网址URL": r"[a-zA-z]+://[^\s]*",
    "手机(国内)": r"0?(13|14|15|17|18|19)[0-9]{9}",
    "固话号码(国内)": r"[0-9-()（）]{7,18}",
    "负浮点数": r"-([1-9]\d*\.\d*|0\.\d*[1-9]\d*)",
    "匹配整数": r"-?[1-9]\d*",
    "正浮点数": r"[1-9]\d*\.\d*|0\.\d*[1-9]\d*",
    "腾讯QQ号": r"[1-9]([0-9]{5,11})",
    "邮政编码": r"\d{6}",
    "IP地址": r"(25[0-5]|2[0-4]\d|[0-1]\d{2}|[1-9]?\d)\.(25[0-5]|2[0-4]\d|[0-1]\d{2}|[1-9]?\d)\.(25[0-5]|2[0-4]\d|[0-1]\d{2}|[1-9]?\d)\.(25[0-5]|2[0-4]\d|[0-1]\d{2}|[1-9]?\d)",
    "身份证号": r"\d{17}[\d|x]|\d{15}",
    "格式日期": r"\d{4}(-|/|.)\d{1,2}\1\d{1,2}",
    "正整数": r"[1-9]\d*",
    "负整数": r"-[1-9]\d*",
    "用户名": r"[A-Za-z0-9_\-\u4e00-\u9fa5]+"
}

LANGUAGE_TEMPLATES = {
    "JavaScript": {
        "match": "const regex = /{pattern}/{flags};\nconst matches = text.match(regex);",
        "test": "const regex = /{pattern}/{flags};\nconst result = regex.test(text);",
        "replace": "const regex = /{pattern}/{flags};\nconst result = text.replace(regex, '{replacement}');",
        "flags": {"g": "g", "i": "i", "m": "m"}
    },
    "Python": {
        "match": "import re\npattern = r'{pattern}'\nmatches = re.findall(pattern, text, flags={flags_value})",
        "test": "import re\npattern = r'{pattern}'\nresult = re.search(pattern, text, flags={flags_value})",
        "replace": "import re\npattern = r'{pattern}'\nresult = re.sub(pattern, '{replacement}', text, flags={flags_value})",
        "flags": {"re.IGNORECASE": "i", "re.MULTILINE": "m", "re.DOTALL": "s"}
    },
    "PHP": {
        "match": "$pattern = '/{pattern}/{flags}';\npreg_match_all($pattern, $text, $matches);",
        "test": "$pattern = '/{pattern}/{flags}';\n$result = preg_match($pattern, $text);",
        "replace": "$pattern = '/{pattern}/{flags}';\n$result = preg_replace($pattern, '{replacement}', $text);",
        "flags": {"i": "i", "m": "m", "s": "s"}
    },
    "Java": {
        "match": "import java.util.regex.*;\nPattern pattern = Pattern.compile(\"{pattern}\", {flags});\nMatcher matcher = pattern.matcher(text);\nwhile(matcher.find()) {{\n    // 处理匹配\n}}",
        "test": "import java.util.regex.*;\nPattern pattern = Pattern.compile(\"{pattern}\", {flags});\nMatcher matcher = pattern.matcher(text);\nboolean result = matcher.find();",
        "replace": "import java.util.regex.*;\nPattern pattern = Pattern.compile(\"{pattern}\", {flags});\nMatcher matcher = pattern.matcher(text);\nString result = matcher.replaceAll(\"{replacement}\");",
        "flags": {"Pattern.CASE_INSENSITIVE": "i", "Pattern.MULTILINE": "m", "Pattern.DOTALL": "s"}
    },
    "Go": {
        "match": "import \"regexp\"\npattern := regexp.MustCompile(`{pattern}`)\nmatches := pattern.FindAllString(text, -1)",
        "test": "import \"regexp\"\npattern := regexp.MustCompile(`{pattern}`)\nresult := pattern.MatchString(text)",
        "replace": "import \"regexp\"\npattern := regexp.MustCompile(`{pattern}`)\nresult := pattern.ReplaceAllString(text, \"{replacement}\")",
        "flags": {"i": "(?i)", "m": "(?m)", "s": "(?s)"}
    },
    "C#": {
        "match": "using System.Text.RegularExpressions;\nRegex pattern = new Regex(@\"{pattern}\", {flags});\nMatchCollection matches = pattern.Matches(text);",
        "test": "using System.Text.RegularExpressions;\nRegex pattern = new Regex(@\"{pattern}\", {flags});\nbool result = pattern.IsMatch(text);",
        "replace": "using System.Text.RegularExpressions;\nRegex pattern = new Regex(@\"{pattern}\", {flags});\nstring result = pattern.Replace(text, \"{replacement}\");",
        "flags": {"RegexOptions.IgnoreCase": "i", "RegexOptions.Multiline": "m", "RegexOptions.Singleline": "s"}
    },
    "Ruby": {
        "match": "pattern = /{pattern}/{flags}\nmatches = text.scan(pattern)",
        "test": "pattern = /{pattern}/{flags}\nresult = !!(text =~ pattern)",
        "replace": "pattern = /{pattern}/{flags}\nresult = text.gsub(pattern, '{replacement}')",
        "flags": {"i": "i", "m": "m"}
    }
}

JSON_CONTENT = '''{
    "store": {
        "book": [
            {
                "category": "reference",
                "author": "Nigel Rees",
                "title": "Sayings of the Century",
                "price": 8.95
            },
            {
                "category": "fiction",
                "author": "Evelyn Waugh",
                "title": "Sword of Honour",
                "price": 12.99
            },
            {
                "category": "fiction",
                "author": "Herman Melville",
                "title": "Moby Dick",
                "isbn": "0-553-21311-3",
                "price": 8.99
            },
            {
                "category": "fiction",
                "author": "J. R. R. Tolkien",
                "title": "The Lord of the Rings",
                "isbn": "0-395-19395-8",
                "price": 22.99
            }
        ],
        "bicycle": {
            "color": "red",
            "price": 19.95
        }
    },
    "expensive": 10
}'''

PLATFORM_MAPPING = {
    "阿里通义千问": "ali",
    "OpenAI GPT": "openai",
    "百度文心一言": "baidu",
    "讯飞星火": "spark",
    "智谱ChatGLM": "glm"
}

STYLE_PREVIEWS = {
    "标准格式": {
        "中文": "用例步骤清晰明确，预期结果具体",
        "英文": "Clear test steps with specific expected results"
    },
    "详细步骤": {
        "中文": "包含详细的操作步骤、输入数据和验证点",
        "英文": "Include detailed operation steps, input data and verification points"
    },
    "简洁格式": {
        "中文": "重点突出，省略非关键步骤",
        "英文": "Focus on key points, omit non-critical steps"
    },
    "BDD格式(Given-When-Then)": {
        "中文": "Given-前提条件, When-执行操作, Then-预期结果",
        "英文": "Given-preconditions, When-actions, Then-expected results"
    }
}

LANGUAGE_DESCRIPTIONS = {
    "中文": "所有内容使用中文",
    "英文": "所有内容使用英文"
}

SIMPLE_EXAMPLE = """需求描述：测试一个简单的计算器加法功能

功能要求：
1. 用户可以输入两个数字
2. 点击计算按钮进行加法运算
3. 显示计算结果

输入验证：
- 只能输入数字
- 不能为空"""

MEDIUM_EXAMPLE = """需求描述：测试用户登录功能

功能要求：
1. 用户可以通过用户名和密码登录系统
2. 支持记住登录状态功能
3. 提供忘记密码功能
4. 登录失败时有适当的错误提示
5. 成功登录后跳转到用户主页

输入验证：
- 用户名：必填，支持邮箱或手机号格式
- 密码：必填，最少6个字符

安全要求：
- 连续5次登录失败后锁定账户30分钟"""

COMPLEX_EXAMPLE = """需求描述：测试电商平台的完整订单流程

功能模块：
1. 商品浏览和搜索
2. 购物车管理
3. 订单创建和支付
4. 订单状态跟踪
5. 售后和退款

业务流程：
- 用户浏览商品并加入购物车
- 用户结算生成订单
- 用户选择支付方式完成支付
- 商家发货并更新物流信息
- 用户确认收货或申请售后"""

# 导出所有常量
__all__ = ['PROVINCES', 'COUNTRIES', 'CATEGORIES', 'PROVINCE_MAP', 'TO_SECONDS', 'RANDOM_STRING_TYPES',
           'PASSWORD_OPTIONS',
           'DOMAINS_PRESET', 'PHONE_TYPES', 'GENDERS', 'TOOL_CATEGORIES', 'CSS_STYLES', 'HEADLINE_STYLES',
           'PROVINCE_CITY_AREA_CODES', 'PREDEFINED_PATTERNS', 'LANGUAGE_TEMPLATES', 'JSON_CONTENT', 'PLATFORM_MAPPING',
           'STYLE_PREVIEWS', 'LANGUAGE_DESCRIPTIONS']

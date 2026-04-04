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
        "description": "文本差异比较、版本对比分析",
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
    /* 全局样式 */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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

    .sub-header {
        font-size: 1.5rem;
        color: #2d3748;
        font-weight: 600;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #667eea;
    }

    /* 工具卡片网格布局 */
    .tools-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }

    .tool-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
        cursor: pointer;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .tool-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        border-color: #667eea;
    }
    /* 选中的卡片样式 */
    .tool-card.selected {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-color: #4c51bf;
        transform: scale(1.02);
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
    }

    .tool-card.selected .tool-icon {
        color: white;
    }

    .tool-card.selected .tool-title {
        color: white;
    }

    .tool-card.selected .tool-desc {
        color: rgba(255, 255, 255, 0.9);
    }

    .tool-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #667eea;
    }

    .tool-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 0.5rem;
    }

    .tool-desc {
        color: #718096;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* 功能区域样式 */
    .section-card {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }

    .category-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* 按钮样式 */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }

    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
    }

    .copy-btn {
        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.5rem;
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.3s ease;
        margin: 5px;
    }

    .copy-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 15px rgba(72, 187, 120, 0.3);
    }

    /* 结果框样式 */
    .result-box {
        background: #f8fafc;
        border: 2px dashed #cbd5e0;
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
        background-color: #f7fafc;
        padding: 0.5rem;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f7fafc;
        border-radius: 8px 8px 0px 0px;
        gap: 1rem;
        padding: 0 1.5rem;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background-color: #667eea !important;
        color: white !important;
    }

    /* 侧边栏样式 */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }

    /* 指标卡片 */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        border-left: 4px solid #667eea;
    }

    /* 响应式调整 */
    @media (max-width: 768px) {
        .tools-grid {
            grid-template-columns: 1fr;
        }

        .main-header {
            font-size: 2rem;
        }
    }

    /* 卡片按钮样式 */
    .card-button {
        background: white !important;
        color: #2d3748 !important;
        border: 1px solid #e2e8f0 !important;
        padding: 1.5rem !important;
        border-radius: 16px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        height: auto !important;
        min-height: 180px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important;
    }

    .card-button:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 20px 40px rgba(0,0,0,0.15) !important;
        border-color: #667eea !important;
        background: white !important;
        color: #2d3748 !important;
    }

    /* 选中状态的卡片按钮 */
    .selected-card-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: 2px solid #4c51bf !important;
        transform: scale(1.02) !important;
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4) !important;
    }

    .selected-card-button:hover {
        background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%) !important;
        color: white !important;
        transform: scale(1.02) !important;
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4) !important;
    }

    .tool-picker-card {
        background:
            radial-gradient(circle at top right, rgba(148, 163, 184, 0.18) 0%, rgba(148, 163, 184, 0) 42%),
            linear-gradient(145deg, #e7edf5 0%, #d8e2ec 56%, #ced9e6 100%);
        border-radius: 16px;
        border: 1px solid #b7c6d8;
        box-shadow:
            0 14px 30px rgba(15, 23, 42, 0.12),
            inset 0 1px 0 rgba(255,255,255,0.72);
        padding: 1.25rem;
        min-height: 188px;
        margin-bottom: 0.75rem;
        transition: all 0.25s ease;
    }

    .tool-picker-card.selected {
        background:
            radial-gradient(circle at top right, rgba(255,255,255,0.24) 0%, rgba(255,255,255,0) 38%),
            linear-gradient(145deg, #d5dfeb 0%, #c0ccdd 56%, #b2c0d4 100%);
        border-color: #8ea3bd;
        box-shadow:
            inset 1px 1px 0 rgba(255,255,255,0.86),
            0 16px 28px rgba(100, 116, 139, 0.2);
        transform: translateY(-1px);
    }

    .tool-picker-icon {
        font-size: 2rem;
        line-height: 1;
        margin-bottom: 0.75rem;
    }

    .tool-picker-title {
        font-size: 1.12rem;
        font-weight: 700;
        color: #17324a;
        margin-bottom: 0.5rem;
    }

    .tool-picker-desc {
        color: #43586d;
        font-size: 0.93rem;
        line-height: 1.55;
        min-height: 3.2rem;
    }

    .tool-picker-card.selected .tool-picker-title {
        color: #122b42;
    }

    .tool-picker-card.selected .tool-picker-desc {
        color: #385168;
    }

    .tool-picker-active-button {
        background: linear-gradient(180deg, #dce5ef 0%, #c2cfde 100%);
        color: #17324a;
        border: 1px solid #92a8c1;
        border-radius: 12px;
        font-weight: 700;
        padding: 0.8rem 1rem;
        text-align: center;
        width: 100%;
        min-height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow:
            inset 1px 1px 0 rgba(255,255,255,0.82),
            inset -1px -1px 0 rgba(126, 145, 167, 0.36);
    }

    .tool-picker-status {
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 0.45rem;
        text-align: center;
        font-weight: 600;
    }
</style>
"""
# 顶部标题区域
HEADLINE_STYLES = """
<div style="text-align: center; padding: 3rem 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 0 0 20px 20px; margin: -1rem -1rem 2rem -1rem;">
    <h1 class="main-header">🔧 测试工程师常用工具集</h1>
    <p style="color: white; font-size: 1.2rem; opacity: 0.9; max-width: 600px; margin: 0 auto;">
        一站式测试数据生成、分析和处理平台
    </p>
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

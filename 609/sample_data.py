from datetime import datetime, timedelta


def create_timestamp(base_time, offset_seconds):
    return (base_time + timedelta(seconds=offset_seconds)).isoformat()


base_time = datetime(2024, 1, 15, 10, 0, 0)

sample_conversations = [
    {
        "id": "conv_001",
        "agent_id": "agent_001",
        "customer_id": "cust_1001",
        "timestamp": create_timestamp(base_time, 0),
        "messages": [
            {
                "role": "customer",
                "content": "你好，我想查询一下我的订单什么时候发货",
                "timestamp": create_timestamp(base_time, 0)
            },
            {
                "role": "service",
                "content": "您好！欢迎咨询，请您提供一下订单号，我马上为您查询。",
                "timestamp": create_timestamp(base_time, 15)
            },
            {
                "role": "customer",
                "content": "订单号是DD20240115001",
                "timestamp": create_timestamp(base_time, 35)
            },
            {
                "role": "service",
                "content": "请您稍等，我正在为您查询订单状态...",
                "timestamp": create_timestamp(base_time, 45)
            },
            {
                "role": "service",
                "content": "您好，已为您查询到订单DD20240115001，目前商品已出库，预计今天下午发货，明天可以送达。请问还有什么可以帮您的吗？",
                "timestamp": create_timestamp(base_time, 75)
            },
            {
                "role": "customer",
                "content": "好的，谢谢！",
                "timestamp": create_timestamp(base_time, 95)
            },
            {
                "role": "service",
                "content": "不客气，感谢您的咨询，祝您生活愉快！",
                "timestamp": create_timestamp(base_time, 105)
            }
        ],
        "post_survey": {
            "satisfaction_score": 5,
            "resolution_rating": 5,
            "attitude_rating": 5,
            "would_recommend": True,
            "comment": "客服很专业，回答清晰，非常满意！"
        }
    },
    {
        "id": "conv_002",
        "agent_id": "agent_002",
        "customer_id": "cust_1002",
        "timestamp": create_timestamp(base_time, 200),
        "messages": [
            {
                "role": "customer",
                "content": "我要退款，这个商品我不想要了",
                "timestamp": create_timestamp(base_time, 200)
            },
            {
                "role": "service",
                "content": "您好，请问订单号是多少呢？",
                "timestamp": create_timestamp(base_time, 260)
            },
            {
                "role": "customer",
                "content": "DD20240114005，还没发货的",
                "timestamp": create_timestamp(base_time, 280)
            },
            {
                "role": "service",
                "content": "知道了，等一下帮你处理",
                "timestamp": create_timestamp(base_time, 380)
            },
            {
                "role": "customer",
                "content": "还要等多久啊？",
                "timestamp": create_timestamp(base_time, 420)
            },
            {
                "role": "service",
                "content": "急什么，我这边忙得很，等着吧",
                "timestamp": create_timestamp(base_time, 480)
            },
            {
                "role": "customer",
                "content": "你这是什么态度？",
                "timestamp": create_timestamp(base_time, 500)
            },
            {
                "role": "service",
                "content": "就这样，你自己看退款政策吧",
                "timestamp": create_timestamp(base_time, 560)
            }
        ],
        "post_survey": {
            "satisfaction_score": 1,
            "resolution_rating": 1,
            "attitude_rating": 1,
            "would_recommend": False,
            "comment": "客服态度非常差，问题也没解决"
        }
    },
    {
        "id": "conv_003",
        "agent_id": "agent_003",
        "customer_id": "cust_1003",
        "timestamp": create_timestamp(base_time, 600),
        "messages": [
            {
                "role": "customer",
                "content": "我的账户登录不上了，一直提示密码错误",
                "timestamp": create_timestamp(base_time, 600)
            },
            {
                "role": "service",
                "content": "您好，很抱歉给您带来不便。请您先尝试点击'忘记密码'进行密码重置操作。",
                "timestamp": create_timestamp(base_time, 620)
            },
            {
                "role": "customer",
                "content": "试过了，收不到验证码短信",
                "timestamp": create_timestamp(base_time, 650)
            },
            {
                "role": "service",
                "content": "请您检查一下手机是否屏蔽了短信，或者确认一下手机号是否正确。如果还是不行，我可以帮您转接技术同事处理。",
                "timestamp": create_timestamp(base_time, 675)
            },
            {
                "role": "customer",
                "content": "手机号没错的，帮我转接吧",
                "timestamp": create_timestamp(base_time, 700)
            },
            {
                "role": "service",
                "content": "好的，请您稍等，我正在为您转接技术支持专员，预计需要1-2分钟。",
                "timestamp": create_timestamp(base_time, 720)
            }
        ],
        "post_survey": {
            "satisfaction_score": 4,
            "resolution_rating": 3,
            "attitude_rating": 5,
            "would_recommend": True,
            "comment": "态度很好，虽然问题需要转接，但至少有在帮忙解决"
        }
    },
    {
        "id": "conv_004",
        "agent_id": "agent_001",
        "customer_id": "cust_1004",
        "timestamp": create_timestamp(base_time, 900),
        "messages": [
            {
                "role": "customer",
                "content": "您好，请问有优惠券吗？",
                "timestamp": create_timestamp(base_time, 900)
            },
            {
                "role": "service",
                "content": "您好！目前新用户可以领取100减20的优惠券，老用户也有专属优惠哦。请问您是新用户还是老用户呢？",
                "timestamp": create_timestamp(base_time, 910)
            },
            {
                "role": "customer",
                "content": "新用户，怎么领？",
                "timestamp": create_timestamp(base_time, 930)
            },
            {
                "role": "service",
                "content": "您可以点击首页顶部的'新人专享'banner，进入后就可以领取优惠券了。优惠券有效期是7天，记得及时使用哦！",
                "timestamp": create_timestamp(base_time, 945)
            },
            {
                "role": "customer",
                "content": "好的，我去看看。谢谢！",
                "timestamp": create_timestamp(base_time, 970)
            },
            {
                "role": "service",
                "content": "不客气！如果在使用过程中有任何问题，欢迎随时咨询。祝您购物愉快！",
                "timestamp": create_timestamp(base_time, 985)
            }
        ],
        "post_survey": {
            "satisfaction_score": 5,
            "resolution_rating": 5,
            "attitude_rating": 5,
            "would_recommend": True,
            "comment": "非常满意，解答清晰，态度友好"
        }
    },
    {
        "id": "conv_005",
        "agent_id": "agent_004",
        "customer_id": "cust_1005",
        "timestamp": create_timestamp(base_time, 1100),
        "messages": [
            {
                "role": "customer",
                "content": "你们这个商品描述和实物不一样啊",
                "timestamp": create_timestamp(base_time, 1100)
            },
            {
                "role": "service",
                "content": "不知道，你自己看详情页吧",
                "timestamp": create_timestamp(base_time, 1200)
            },
            {
                "role": "customer",
                "content": "我看了，但是收到的货颜色不一样",
                "timestamp": create_timestamp(base_time, 1230)
            },
            {
                "role": "service",
                "content": "那没办法，商品页面写了以实物为准",
                "timestamp": create_timestamp(base_time, 1350)
            },
            {
                "role": "customer",
                "content": "那我要退货",
                "timestamp": create_timestamp(base_time, 1380)
            },
            {
                "role": "service",
                "content": "退就退呗，自己申请去",
                "timestamp": create_timestamp(base_time, 1500)
            }
        ],
        "post_survey": {
            "satisfaction_score": 1,
            "resolution_rating": 1,
            "attitude_rating": 1,
            "would_recommend": False,
            "comment": "极其不满意，客服完全不负责"
        }
    },
    {
        "id": "conv_006",
        "agent_id": "agent_005",
        "customer_id": "cust_1006",
        "timestamp": create_timestamp(base_time, 1700),
        "messages": [
            {
                "role": "customer",
                "content": "请问会员有什么福利？",
                "timestamp": create_timestamp(base_time, 1700)
            },
            {
                "role": "service",
                "content": "您好，成为我们的会员可以享受以下福利：1. 每月赠送100积分；2. 专属会员价；3. 生日当月双倍积分；4. 优先客服通道。请问您想了解哪项的详细信息呢？",
                "timestamp": create_timestamp(base_time, 1725)
            },
            {
                "role": "customer",
                "content": "积分怎么用？",
                "timestamp": create_timestamp(base_time, 1750)
            },
            {
                "role": "service",
                "content": "积分可以在下单时直接抵扣现金，100积分=1元，也可以在积分商城兑换礼品。积分有效期是一年，请记得及时使用哦。",
                "timestamp": create_timestamp(base_time, 1770)
            },
            {
                "role": "customer",
                "content": "好的，了解了，谢谢！",
                "timestamp": create_timestamp(base_time, 1795)
            },
            {
                "role": "service",
                "content": "不客气！如果还有其他问题，欢迎随时咨询。祝您生活愉快！",
                "timestamp": create_timestamp(base_time, 1810)
            }
        ],
        "post_survey": {
            "satisfaction_score": 5,
            "resolution_rating": 5,
            "attitude_rating": 5,
            "would_recommend": True,
            "comment": "回答详细，服务热情，非常满意"
        }
    },
    {
        "id": "conv_007",
        "agent_id": "agent_002",
        "customer_id": "cust_1007",
        "timestamp": create_timestamp(base_time, 2000),
        "messages": [
            {
                "role": "customer",
                "content": "发货太慢了，都三天了还没发",
                "timestamp": create_timestamp(base_time, 2000)
            },
            {
                "role": "service",
                "content": "哦，我帮你看看",
                "timestamp": create_timestamp(base_time, 2100)
            },
            {
                "role": "service",
                "content": "你的订单显示缺货，等吧",
                "timestamp": create_timestamp(base_time, 2200)
            },
            {
                "role": "customer",
                "content": "那什么时候有货？",
                "timestamp": create_timestamp(base_time, 2230)
            },
            {
                "role": "service",
                "content": "不知道，等着吧",
                "timestamp": create_timestamp(base_time, 2350)
            }
        ],
        "post_survey": {
            "satisfaction_score": 1,
            "resolution_rating": 1,
            "attitude_rating": 2,
            "would_recommend": False,
            "comment": "客服敷衍了事，信息不透明"
        }
    },
    {
        "id": "conv_008",
        "agent_id": "agent_006",
        "customer_id": "cust_1008",
        "timestamp": create_timestamp(base_time, 2500),
        "messages": [
            {
                "role": "customer",
                "content": "我的快递显示签收了，但我没收到",
                "timestamp": create_timestamp(base_time, 2500)
            },
            {
                "role": "service",
                "content": "您好，非常抱歉给您带来困扰。请您先检查一下小区快递柜或物业代收点，有些快递会放在那里。",
                "timestamp": create_timestamp(base_time, 2520)
            },
            {
                "role": "customer",
                "content": "都找过了，没有",
                "timestamp": create_timestamp(base_time, 2550)
            },
            {
                "role": "service",
                "content": "好的，请您提供一下订单号，我帮您联系快递网点核实情况。",
                "timestamp": create_timestamp(base_time, 2570)
            },
            {
                "role": "customer",
                "content": "DD20240110008",
                "timestamp": create_timestamp(base_time, 2590)
            },
            {
                "role": "service",
                "content": "请您稍等，我正在联系快递方...",
                "timestamp": create_timestamp(base_time, 2610)
            },
            {
                "role": "service",
                "content": "您好，已联系快递员，他说放在您家门口的消防栓旁边了，您再去看看？如果确实没有，我们可以为您安排补发或者退款。",
                "timestamp": create_timestamp(base_time, 2700)
            },
            {
                "role": "customer",
                "content": "找到了，谢谢！",
                "timestamp": create_timestamp(base_time, 2730)
            },
            {
                "role": "service",
                "content": "太好了！感谢您的耐心配合，如有其他问题欢迎随时联系。祝您生活愉快！",
                "timestamp": create_timestamp(base_time, 2750)
            }
        ],
        "post_survey": {
            "satisfaction_score": 5,
            "resolution_rating": 5,
            "attitude_rating": 5,
            "would_recommend": True,
            "comment": "客服积极帮忙解决问题，态度很好，最终问题也解决了"
        }
    }
]

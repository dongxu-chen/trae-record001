from data_store import DataStore
from models import User, Book, Rating, SocialConnection, BookSeries
from datetime import datetime


def create_sample_data(data_store: DataStore):
    books = [
        Book(book_id=1, title="三体", author="刘慈欣", genres=["科幻", "悬疑"], year=2008, total_pages=302, series_id=1, series_order=1),
        Book(book_id=2, title="黑暗森林", author="刘慈欣", genres=["科幻", "悬疑"], year=2008, total_pages=446, series_id=1, series_order=2),
        Book(book_id=3, title="死神永生", author="刘慈欣", genres=["科幻", "哲学"], year=2010, total_pages=513, series_id=1, series_order=3),
        Book(book_id=4, title="百年孤独", author="马尔克斯", genres=["魔幻现实主义", "经典"], year=1967, total_pages=360),
        Book(book_id=5, title="活着", author="余华", genres=["现实", "经典"], year=1993, total_pages=191),
        Book(book_id=6, title="围城", author="钱钟书", genres=["讽刺", "经典"], year=1947, total_pages=359),
        Book(book_id=7, title="红楼梦", author="曹雪芹", genres=["古典", "爱情"], year=1791, total_pages=1606),
        Book(book_id=8, title="西游记", author="吴承恩", genres=["古典", "神话"], year=1592, total_pages=872),
        Book(book_id=9, title="1984", author="乔治·奥威尔", genres=["反乌托邦", "政治"], year=1949, total_pages=328, series_id=2, series_order=1),
        Book(book_id=10, title="动物农场", author="乔治·奥威尔", genres=["反乌托邦", "政治"], year=1945, total_pages=112, series_id=2, series_order=2),
        Book(book_id=11, title="哈利波特与魔法石", author="J.K.罗琳", genres=["奇幻", "冒险"], year=1997, total_pages=223, series_id=3, series_order=1),
        Book(book_id=12, title="指环王", author="托尔金", genres=["奇幻", "冒险"], year=1954, total_pages=1178, series_id=4, series_order=1),
        Book(book_id=13, title="小王子", author="圣埃克苏佩里", genres=["童话", "哲学"], year=1943, total_pages=96),
        Book(book_id=14, title="了不起的盖茨比", author="菲茨杰拉德", genres=["经典", "美国文学"], year=1925, total_pages=180),
        Book(book_id=15, title="老人与海", author="海明威", genres=["经典", "美国文学"], year=1952, total_pages=128),
        Book(book_id=16, title="追风筝的人", author="卡勒德·胡赛尼", genres=["温情", "成长"], year=2003, total_pages=362),
        Book(book_id=17, title="解忧杂货店", author="东野圭吾", genres=["治愈", "温情"], year=2012, total_pages=291),
        Book(book_id=18, title="白夜行", author="东野圭吾", genres=["悬疑", "推理"], year=1999, total_pages=352, series_id=5, series_order=1),
        Book(book_id=19, title="嫌疑人X的献身", author="东野圭吾", genres=["悬疑", "推理"], year=2005, total_pages=251, series_id=5, series_order=2),
        Book(book_id=20, title="人类简史", author="尤瓦尔·赫拉利", genres=["历史", "社科"], year=2011, total_pages=440),
    ]
    
    for book in books:
        data_store.add_book(book)

    users = [
        User(user_id=1, username="小明", age=25, gender="男", favorite_genres=["科幻", "悬疑"]),
        User(user_id=2, username="小红", age=23, gender="女", favorite_genres=["经典", "爱情"]),
        User(user_id=3, username="小刚", age=28, gender="男", favorite_genres=["科幻", "奇幻"]),
        User(user_id=4, username="小丽", age=26, gender="女", favorite_genres=["治愈", "温情"]),
        User(user_id=5, username="小华", age=30, gender="男", favorite_genres=["历史", "社科"]),
        User(user_id=6, username="小美", age=24, gender="女", favorite_genres=["奇幻", "冒险"]),
        User(user_id=7, username="小强", age=27, gender="男", favorite_genres=["悬疑", "推理"]),
        User(user_id=8, username="小芳", age=22, gender="女", favorite_genres=["古典", "神话"]),
        User(user_id=9, username="新用户一", age=20, gender="男", favorite_genres=["科幻"]),
        User(user_id=10, username="新用户二", age=21, gender="女", favorite_genres=None),
    ]
    
    for user in users:
        data_store.add_user(user)

    ratings = [
        Rating(user_id=1, book_id=1, rating=5.0),
        Rating(user_id=1, book_id=2, rating=4.8),
        Rating(user_id=1, book_id=3, rating=4.5),
        Rating(user_id=1, book_id=9, rating=4.0),
        Rating(user_id=1, book_id=18, rating=4.2),
        Rating(user_id=1, book_id=19, rating=4.7),
        
        Rating(user_id=2, book_id=4, rating=4.5),
        Rating(user_id=2, book_id=5, rating=5.0),
        Rating(user_id=2, book_id=6, rating=4.0),
        Rating(user_id=2, book_id=7, rating=4.8),
        Rating(user_id=2, book_id=13, rating=4.5),
        
        Rating(user_id=3, book_id=1, rating=4.5),
        Rating(user_id=3, book_id=2, rating=4.7),
        Rating(user_id=3, book_id=11, rating=4.8),
        Rating(user_id=3, book_id=12, rating=5.0),
        Rating(user_id=3, book_id=9, rating=4.0),
        
        Rating(user_id=4, book_id=16, rating=5.0),
        Rating(user_id=4, book_id=17, rating=4.8),
        Rating(user_id=4, book_id=13, rating=4.5),
        Rating(user_id=4, book_id=5, rating=4.2),
        
        Rating(user_id=5, book_id=20, rating=5.0),
        Rating(user_id=5, book_id=9, rating=4.5),
        Rating(user_id=5, book_id=10, rating=4.3),
        
        Rating(user_id=6, book_id=11, rating=5.0),
        Rating(user_id=6, book_id=12, rating=4.8),
        Rating(user_id=6, book_id=8, rating=4.0),
        
        Rating(user_id=7, book_id=18, rating=5.0),
        Rating(user_id=7, book_id=19, rating=4.9),
        Rating(user_id=7, book_id=2, rating=4.5),
        
        Rating(user_id=8, book_id=7, rating=4.8),
        Rating(user_id=8, book_id=8, rating=4.5),
        Rating(user_id=8, book_id=4, rating=4.0),
    ]
    
    for rating in ratings:
        data_store.add_rating(rating)

    social_connections = [
        SocialConnection(user_id=1, friend_id=2),
        SocialConnection(user_id=1, friend_id=3),
        SocialConnection(user_id=1, friend_id=7),
        SocialConnection(user_id=2, friend_id=4),
        SocialConnection(user_id=2, friend_id=8),
        SocialConnection(user_id=3, friend_id=5),
        SocialConnection(user_id=3, friend_id=6),
        SocialConnection(user_id=4, friend_id=6),
        SocialConnection(user_id=5, friend_id=6),
        SocialConnection(user_id=7, friend_id=8),
    ]
    
    for conn in social_connections:
        data_store.add_social_connection(conn)

    book_series = [
        BookSeries(series_id=1, series_name="三体三部曲", author="刘慈欣", description="地球文明与三体文明的史诗级碰撞", total_books=3),
        BookSeries(series_id=2, series_name="奥威尔反乌托邦系列", author="乔治·奥威尔", description="对极权主义的深刻警示", total_books=2),
        BookSeries(series_id=3, series_name="哈利波特系列", author="J.K.罗琳", description="少年魔法师的成长冒险", total_books=7),
        BookSeries(series_id=4, series_name="指环王系列", author="托尔金", description="中土世界的壮丽史诗", total_books=3),
        BookSeries(series_id=5, series_name="东野圭吾推理系列", author="东野圭吾", description="社会派推理代表作", total_books=2),
    ]
    
    for series in book_series:
        data_store.add_book_series(series)
    
    for book in books:
        if book.series_id and book.series_order:
            data_store.add_book_to_series(book.book_id, book.series_id, book.series_order)

    print(f"已加载 {len(books)} 本书")
    print(f"已加载 {len(users)} 个用户")
    print(f"已加载 {len(ratings)} 条评分")
    print(f"已加载 {len(social_connections)} 条社交关系")
    print(f"已加载 {len(book_series)} 个系列丛书")


if __name__ == "__main__":
    ds = DataStore()
    create_sample_data(ds)
    print("\n数据加载完成！")

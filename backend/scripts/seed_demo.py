"""Populate the local SQLite database with reusable UI demo data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.api.auth import get_password_hash
from app.db import engine, init_db
from app.models.models import (
    Announcement,
    AnnouncementStatus,
    Comment,
    CommentTargetType,
    Competition,
    CompetitionEntry,
    CompetitionScoreType,
    CompetitionStatus,
    Favorite,
    FavoriteTargetType,
    Follow,
    Like,
    LikeTargetType,
    Notification,
    NotificationType,
    Post,
    PostType,
    Rating,
    Soup,
    SoupCollection,
    SoupTag,
    Tag,
    TagKind,
    TagStatus,
    ThemePreference,
    User,
    UserRole,
    UserStatus,
    UserUidAllocator,
)


ROOT_PASSWORD = "RootTest!2026"
DEMO_PASSWORD = "DemoUser!2026"


USER_SPECS = (
    {
        "username": "root",
        "nickname": "Root 管理员",
        "email": "root@demo.example.com",
        "password": ROOT_PASSWORD,
        "role": UserRole.ROOT,
        "points": 2680,
        "bio": "SQLite 演示环境的 root 管理账号。",
        "theme_preference": ThemePreference.SYSTEM,
    },
    {
        "username": "tangyuan",
        "nickname": "汤圆侦探",
        "email": "tangyuan@demo.example.com",
        "password": DEMO_PASSWORD,
        "role": UserRole.USER,
        "points": 920,
        "bio": "喜欢从日常细节里找出不合理之处。",
        "theme_preference": ThemePreference.LIGHT,
    },
    {
        "username": "night_reader",
        "nickname": "夜航读者",
        "email": "night-reader@demo.example.com",
        "password": DEMO_PASSWORD,
        "role": UserRole.USER,
        "points": 1460,
        "bio": "偏爱黑汤和带有时间诡计的故事。",
        "theme_preference": ThemePreference.DARK,
    },
)


TAG_SPECS = (
    ("demo-contest", "演示赛", "用于本地演示比赛的固定标签。"),
    ("logic", "逻辑推理", "以线索和逻辑链条为主的谜题。"),
    ("reversal", "反转", "结局会改变对汤面的理解。"),
    ("daily-life", "日常", "从生活场景出发的谜题。"),
    ("suspense", "悬疑", "带有紧张或未知氛围的故事。"),
    ("warm", "温情", "真相中带有温暖情绪的故事。"),
)


SOUP_SPECS = (
    {
        "title": "凌晨四点的敲门声",
        "author": "root",
        "puzzle": "男人连续七天在凌晨四点听见敲门声。第八天敲门声没有出现，他却立刻报警了。为什么？",
        "solution": "男人是公寓管理员。独居老人每天凌晨四点出门送报，都会顺手敲一下值班室的门报平安。第八天没有敲门，意味着老人可能发生了意外。警方和急救人员及时赶到并救下了老人。",
        "tag_slugs": ("demo-contest", "logic", "daily-life"),
        "genre": "本格",
        "soup_color": "清汤",
        "main_player_count": "管理员、独居老人",
        "secondary_player_count": "警察、急救人员",
        "status": "revealed",
        "view_count": 386,
    },
    {
        "title": "不会融化的雪人",
        "author": "tangyuan",
        "puzzle": "盛夏的商场里摆着一个雪人。停电三小时后，雪人完好无损，保安却因此抓住了小偷。为什么？",
        "solution": "雪人不是冰做的，而是珠宝店用白色展示盒拼成的宣传装置。停电后监控失效，小偷移动了其中一个展示盒偷走珠宝，却没有按原来的编号放回。保安从雪人的细微错位锁定了他。",
        "tag_slugs": ("demo-contest", "reversal", "logic"),
        "genre": "变格",
        "soup_color": "清汤",
        "main_player_count": "保安、小偷",
        "secondary_player_count": "珠宝店员",
        "status": "published",
        "view_count": 291,
    },
    {
        "title": "第七码头的空船",
        "author": "night_reader",
        "puzzle": "一艘没有乘客的渡船准时靠岸。船长看到码头上的欢迎横幅后，马上调头离开。为什么？",
        "solution": "这是一场灾害疏散演练，空船本应去第六码头接人。欢迎横幅写着另一支队伍的编号，船长意识到导航标记被风吹错了位置。继续停靠会堵住真正的救援通道，所以立即离开。",
        "tag_slugs": ("demo-contest", "logic", "suspense"),
        "genre": "本格",
        "soup_color": "红汤",
        "main_player_count": "船长",
        "secondary_player_count": "演练人员、码头工作人员",
        "status": "revealed",
        "view_count": 244,
    },
    {
        "title": "只亮一层的电梯",
        "author": "root",
        "puzzle": "写字楼停电后，电梯面板只有十七层的按钮亮着。维修员看了一眼，反而说供电系统没有故障。为什么？",
        "solution": "大楼正在进行消防演习，电梯进入消防员专用模式。十七层是本次演习设定的火警层，亮灯只是定位提示，备用供电和控制系统都在正常工作。",
        "tag_slugs": ("demo-contest", "daily-life", "logic"),
        "genre": "本格",
        "soup_color": "清汤",
        "main_player_count": "维修员",
        "secondary_player_count": "消防演习人员",
        "status": "published",
        "view_count": 198,
    },
    {
        "title": "她每天都买两张票",
        "author": "tangyuan",
        "puzzle": "女人每天独自走进电影院，却总买相邻的两张票。一个月后，售票员终于明白原因，并送给她一张票。为什么？",
        "solution": "女人正在替行动不便的父亲记录老电影重映。父亲年轻时总和母亲坐在固定的两个座位上；母亲去世后，他仍希望那个位置被保留。售票员得知故事后，用员工赠票替她保留了纪念的座位。",
        "tag_slugs": ("warm", "daily-life", "reversal"),
        "genre": "变格",
        "soup_color": "红汤",
        "main_player_count": "女人、父亲",
        "secondary_player_count": "售票员、母亲",
        "status": "revealed",
        "view_count": 427,
    },
    {
        "title": "会说谢谢的闹钟",
        "author": "night_reader",
        "puzzle": "男人每天被闹钟叫醒后，闹钟都会说谢谢。某天闹钟没有道谢，男人却很高兴。为什么？",
        "solution": "闹钟是他给孩子制作的语音打卡装置。孩子按时起床并关闭闹钟后，装置会播放录好的“谢谢”。那天没有播放，是因为孩子已经放假回家，提前亲自叫醒了父亲。",
        "tag_slugs": ("warm", "daily-life"),
        "genre": "鳖汤",
        "soup_color": "清汤",
        "main_player_count": "男人、孩子",
        "secondary_player_count": "无",
        "status": "revealed",
        "view_count": 176,
    },
)


POST_SPECS = (
    {
        "title": "新手提问：怎样写出信息公平的汤面？",
        "author": "tangyuan",
        "content": "刚开始写海龟汤，最担心关键线索只有作者知道。大家会怎样检查汤面是否公平？我目前会先列出事实、误导和可追问线索三栏。",
        "tags": ["创作", "新手"],
        "view_count": 138,
    },
    {
        "title": "本周猜汤复盘：先确认时间线真的很有用",
        "author": "night_reader",
        "content": "整理了这周参与的三局猜汤。比起直接猜身份，先问事件发生顺序、叙述者看到什么，通常更快排除错误方向。欢迎补充自己的提问习惯。",
        "tags": ["复盘", "技巧"],
        "view_count": 203,
    },
    {
        "title": "演示环境使用说明与反馈帖",
        "author": "root",
        "content": "这是本地 SQLite 演示数据的反馈帖。可以在这里测试点赞、收藏、评论、搜索和个人主页，也可以用 root 账号进入管理后台。",
        "tags": ["公告", "演示"],
        "view_count": 512,
    },
    {
        "title": "你更喜欢清汤、红汤还是黑汤？",
        "author": "tangyuan",
        "content": "我最近更喜欢清汤，线索干净，复盘时能看到完整的逻辑闭环。大家最常玩的汤色是什么？理由也可以一起说说。",
        "tags": ["闲聊", "汤色"],
        "view_count": 166,
    },
    {
        "title": "夏夜推理赛创作日志",
        "author": "night_reader",
        "content": "比赛作品已经改到第三版。第一版反转太依赖巧合，第二版人物动机不足，现在把重点放回时间线和可验证的物证上。",
        "tags": ["比赛", "创作日志"],
        "view_count": 229,
    },
)


RATING_SCORES = (
    (9.5, 8.5, 9.0),
    (8.5, 9.0, 8.0),
    (9.0, 8.0, 9.5),
    (8.0, 8.5, 8.5),
    (9.5, 9.0, 9.0),
    (7.5, 8.5, 8.0),
)


def _upsert_users(db: Session, now: datetime) -> dict[str, User]:
    users: dict[str, User] = {}
    for index, spec in enumerate(USER_SPECS):
        user = db.exec(select(User).where(User.username == spec["username"])).first()
        if user is None:
            user = User(
                username=spec["username"],
                nickname=spec["nickname"],
                email=spec["email"],
                hashed_password="",
                created_at=now - timedelta(days=60 - index * 8),
            )
            db.add(user)
            db.flush()
        user.nickname = spec["nickname"]
        user.email = spec["email"]
        user.hashed_password = get_password_hash(spec["password"])
        user.role = spec["role"]
        user.status = UserStatus.ACTIVE
        user.points = spec["points"]
        user.bio = spec["bio"]
        user.allow_bulk_email = True
        user.theme_preference = spec["theme_preference"]
        user.notification_prefs = {
            "registration_date": (now - timedelta(days=60 - index * 8)).date().isoformat()
        }
        user.updated_at = now
        users[user.username] = user
    db.flush()

    max_uid = max(user.uid for user in users.values() if user.uid is not None)
    allocator = db.get(UserUidAllocator, 1)
    if allocator is None:
        db.add(UserUidAllocator(id=1, next_uid=max_uid + 1))
    else:
        allocator.next_uid = max(allocator.next_uid, max_uid + 1)
    db.flush()
    return users


def _upsert_tags(db: Session, now: datetime) -> dict[str, Tag]:
    tags: dict[str, Tag] = {}
    for sort_order, (slug, name, description) in enumerate(TAG_SPECS, start=10):
        tag = db.exec(select(Tag).where(Tag.slug == slug)).first()
        if tag is None:
            tag = Tag(slug=slug, name=name, created_at=now - timedelta(days=30))
            db.add(tag)
            db.flush()
        tag.name = name
        tag.kind = TagKind.CUSTOM
        tag.status = TagStatus.ACTIVE
        tag.description = description
        tag.sort_order = sort_order
        tag.updated_at = now
        tags[slug] = tag
    db.flush()
    return tags


def _upsert_collection(db: Session, owner_uid: int, now: datetime) -> SoupCollection:
    collection = db.exec(
        select(SoupCollection).where(
            SoupCollection.owner_uid == owner_uid,
            SoupCollection.name == "演示谜题集",
        )
    ).first()
    if collection is None:
        collection = SoupCollection(
            owner_uid=owner_uid,
            name="演示谜题集",
            created_at=now - timedelta(days=24),
        )
        db.add(collection)
        db.flush()
    collection.description = "用于测试合集、列表和详情页的本地演示海龟汤。"
    collection.updated_at = now
    return collection


def _upsert_soups(
    db: Session,
    users: dict[str, User],
    tags: dict[str, Tag],
    collection: SoupCollection,
    now: datetime,
) -> list[Soup]:
    soups: list[Soup] = []
    for index, spec in enumerate(SOUP_SPECS):
        author = users[spec["author"]]
        soup = db.exec(
            select(Soup).where(
                Soup.author_uid == author.uid,
                Soup.title == spec["title"],
            )
        ).first()
        if soup is None:
            soup = Soup(
                author_uid=author.uid,
                title=spec["title"],
                puzzle=spec["puzzle"],
                solution=spec["solution"],
                created_at=now - timedelta(days=18 - index * 2),
            )
            db.add(soup)
            db.flush()
        soup.collection_id = collection.id if author.username == "root" else None
        soup.title = spec["title"]
        soup.puzzle = spec["puzzle"]
        soup.solution = spec["solution"]
        soup.tags = [tags[slug].name for slug in spec["tag_slugs"]]
        soup.genre = spec["genre"]
        soup.soup_color = spec["soup_color"]
        soup.main_player_count = spec["main_player_count"]
        soup.secondary_player_count = spec["secondary_player_count"]
        soup.status = spec["status"]
        soup.view_count = spec["view_count"]
        soup.updated_at = now
        soups.append(soup)
        db.flush()

        for slug in spec["tag_slugs"]:
            tag = tags[slug]
            link = db.exec(
                select(SoupTag).where(
                    SoupTag.soup_id == soup.id,
                    SoupTag.tag_id == tag.id,
                )
            ).first()
            if link is None:
                db.add(SoupTag(soup_id=soup.id, tag_id=tag.id, created_at=soup.created_at))
    db.flush()
    return soups


def _upsert_posts(db: Session, users: dict[str, User], now: datetime) -> list[Post]:
    posts: list[Post] = []
    for index, spec in enumerate(POST_SPECS):
        author = users[spec["author"]]
        post = db.exec(
            select(Post).where(
                Post.author_uid == author.uid,
                Post.title == spec["title"],
            )
        ).first()
        if post is None:
            post = Post(
                author_uid=author.uid,
                title=spec["title"],
                content=spec["content"],
                created_at=now - timedelta(days=12 - index * 2),
            )
            db.add(post)
            db.flush()
        post.title = spec["title"]
        post.content = spec["content"]
        post.section = "general"
        post.post_type = PostType.NORMAL
        post.tags = spec["tags"]
        post.status = "published"
        post.view_count = spec["view_count"]
        post.updated_at = now
        posts.append(post)
    db.flush()
    return posts


def _upsert_ratings(db: Session, users: list[User], soups: list[Soup], now: datetime) -> None:
    for soup, scores in zip(soups, RATING_SCORES, strict=True):
        for user, score in zip(users, scores, strict=True):
            rating = db.exec(
                select(Rating).where(
                    Rating.user_uid == user.uid,
                    Rating.soup_id == soup.id,
                )
            ).first()
            if rating is None:
                rating = Rating(
                    user_uid=user.uid,
                    soup_id=soup.id,
                    score=score,
                    created_at=now - timedelta(days=6),
                )
                db.add(rating)
            rating.score = score
            rating.updated_at = now


def _ensure_like(
    db: Session,
    user_uid: int,
    target_type: LikeTargetType,
    target_id: int,
    created_at: datetime,
) -> None:
    exists = db.exec(
        select(Like).where(
            Like.user_uid == user_uid,
            Like.target_type == target_type,
            Like.target_id == target_id,
        )
    ).first()
    if exists is None:
        db.add(
            Like(
                user_uid=user_uid,
                target_type=target_type,
                target_id=target_id,
                created_at=created_at,
            )
        )


def _ensure_favorite(
    db: Session,
    user_uid: int,
    target_type: FavoriteTargetType,
    target_id: int,
    created_at: datetime,
) -> None:
    exists = db.exec(
        select(Favorite).where(
            Favorite.user_uid == user_uid,
            Favorite.target_type == target_type,
            Favorite.target_id == target_id,
        )
    ).first()
    if exists is None:
        db.add(
            Favorite(
                user_uid=user_uid,
                target_type=target_type,
                target_id=target_id,
                created_at=created_at,
            )
        )


def _upsert_reactions(
    db: Session,
    users: list[User],
    soups: list[Soup],
    posts: list[Post],
    now: datetime,
) -> None:
    for soup_index, soup in enumerate(soups):
        for user in users[: 1 + soup_index % 3]:
            _ensure_like(db, user.uid, LikeTargetType.SOUP, soup.id, now - timedelta(days=4))
        for user in users[1 : 2 + soup_index % 2]:
            _ensure_favorite(
                db,
                user.uid,
                FavoriteTargetType.SOUP,
                soup.id,
                now - timedelta(days=3),
            )

    for post_index, post in enumerate(posts):
        for user in users[post_index % 2 :]:
            _ensure_like(db, user.uid, LikeTargetType.POST, post.id, now - timedelta(days=2))
        _ensure_favorite(
            db,
            users[(post_index + 1) % len(users)].uid,
            FavoriteTargetType.POST,
            post.id,
            now - timedelta(days=1),
        )


def _upsert_comment(
    db: Session,
    author_uid: int,
    target_type: CommentTargetType,
    target_id: int,
    content: str,
    created_at: datetime,
) -> Comment:
    comment = db.exec(
        select(Comment).where(
            Comment.author_uid == author_uid,
            Comment.target_type == target_type,
            Comment.target_id == target_id,
            Comment.content == content,
        )
    ).first()
    if comment is None:
        comment = Comment(
            author_uid=author_uid,
            target_type=target_type,
            target_id=target_id,
            content=content,
            created_at=created_at,
        )
        db.add(comment)
        db.flush()
    comment.status = "published"
    comment.updated_at = created_at
    return comment


def _upsert_comments(
    db: Session,
    users: list[User],
    soups: list[Soup],
    posts: list[Post],
    now: datetime,
) -> list[Comment]:
    comments: list[Comment] = []
    soup_texts = (
        "先确认敲门是不是双方约定好的信号，思路就打开了。",
        "展示盒这个反转很适合多人局，线索也能逐步问出来。",
        "我一开始把空船当成事故，原来关键是码头位置。",
        "消防模式解释了为什么只有一个楼层亮灯。",
        "两张票不是给两个人看电影，这个情感落点很舒服。",
        "最后一句很轻松，适合用来做一局收尾。",
    )
    for index, (soup, content) in enumerate(zip(soups, soup_texts, strict=True)):
        comments.append(
            _upsert_comment(
                db,
                users[(index + 1) % len(users)].uid,
                CommentTargetType.SOUP,
                soup.id,
                content,
                now - timedelta(days=3, hours=index),
            )
        )

    post_texts = (
        "我会让完全不知道答案的人试玩一遍，卡住的位置通常就是缺线索的地方。",
        "时间线问题确实高效，我还会先确认地点有没有发生变化。",
        "已测试搜索和排行榜，数据量正好能看出排序差异。",
        "清汤适合认真推，黑汤更适合夜场氛围。",
        "期待正式作品，减少巧合之后会更耐复盘。",
    )
    for index, (post, content) in enumerate(zip(posts, post_texts, strict=True)):
        comments.append(
            _upsert_comment(
                db,
                users[(index + 2) % len(users)].uid,
                CommentTargetType.POST,
                post.id,
                content,
                now - timedelta(days=2, hours=index),
            )
        )
    db.flush()

    for index, comment in enumerate(comments[:4]):
        _ensure_like(
            db,
            users[index % len(users)].uid,
            LikeTargetType.COMMENT,
            comment.id,
            now - timedelta(days=1),
        )
    return comments


def _upsert_social(db: Session, users: list[User], now: datetime) -> None:
    pairs = (
        (users[0].uid, users[1].uid),
        (users[0].uid, users[2].uid),
        (users[1].uid, users[2].uid),
        (users[2].uid, users[0].uid),
    )
    for follower_uid, followed_uid in pairs:
        exists = db.exec(
            select(Follow).where(
                Follow.follower_uid == follower_uid,
                Follow.followed_uid == followed_uid,
            )
        ).first()
        if exists is None:
            db.add(
                Follow(
                    follower_uid=follower_uid,
                    followed_uid=followed_uid,
                    created_at=now - timedelta(days=5),
                )
            )


def _upsert_competition(
    db: Session,
    root: User,
    tags: dict[str, Tag],
    soups: list[Soup],
    now: datetime,
) -> Competition:
    name = "2026 夏夜推理创作赛（演示）"
    competition = db.exec(select(Competition).where(Competition.name == name)).first()
    if competition is None:
        competition = Competition(
            creator_uid=root.uid,
            name=name,
            description="围绕日常场景创作一碗线索公平、可以逐步推理的海龟汤。",
            start_time=now - timedelta(days=7),
            end_time=now + timedelta(days=21),
            created_at=now - timedelta(days=8),
        )
        db.add(competition)
        db.flush()
    competition.creator_uid = root.uid
    competition.description = "围绕日常场景创作一碗线索公平、可以逐步推理的海龟汤。当前为本地演示赛，可用于测试比赛列表、详情和作品排名。"
    competition.start_time = now - timedelta(days=7)
    competition.end_time = now + timedelta(days=21)
    competition.required_tag_ids = [tags["demo-contest"].id]
    competition.optional_tag_ids = [tags["reversal"].id, tags["logic"].id]
    competition.competition_color = "#0E7490"
    competition.score_type = CompetitionScoreType.AVERAGE
    competition.scoring_at = None
    competition.top_n = 4
    competition.custom_page_config = {}
    competition.status = CompetitionStatus.ONGOING
    competition.settled_at = None
    competition.updated_at = now
    db.flush()

    ranked_soups = sorted(soups[:4], key=lambda item: item.avg_rating, reverse=True)
    for rank, soup in enumerate(ranked_soups, start=1):
        entry = db.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == competition.id,
                CompetitionEntry.soup_id == soup.id,
            )
        ).first()
        if entry is None:
            entry = CompetitionEntry(
                competition_id=competition.id,
                soup_id=soup.id,
                author_uid=soup.author_uid,
                created_at=soup.created_at,
            )
            db.add(entry)
        entry.author_uid = soup.author_uid
        entry.final_score = soup.avg_rating
        entry.rank = rank
    return competition


def _upsert_announcement(db: Session, root: User, now: datetime) -> None:
    title = "欢迎使用汤吧社区本地演示环境"
    announcement = db.exec(
        select(Announcement).where(Announcement.title == title)
    ).first()
    if announcement is None:
        announcement = Announcement(
            author_uid=root.uid,
            title=title,
            content="演示账号和内容已经准备完成，可以测试搜索、排行榜、比赛、互动与管理功能。",
            created_at=now - timedelta(days=2),
        )
        db.add(announcement)
    announcement.author_uid = root.uid
    announcement.content = "演示账号和内容已经准备完成，可以测试搜索、排行榜、比赛、互动与管理功能。所有内容均保存在本地 SQLite 数据库中。"
    announcement.priority = 80
    announcement.status = AnnouncementStatus.PUBLISHED
    announcement.expires_at = None
    announcement.published_at = announcement.published_at or now - timedelta(days=2)
    announcement.updated_at = now


def _upsert_notifications(
    db: Session,
    users: list[User],
    competition: Competition,
    now: datetime,
) -> None:
    specs = (
        (users[0], "演示环境已准备好", "root 账号、演示内容和关联互动数据已经写入。", False),
        (users[1], "夏夜推理赛进行中", "你的作品已加入本地演示比赛。", False),
        (users[2], "收到新的互动", "有人评论了你的海龟汤，去看看吧。", True),
    )
    for user, title, content, is_read in specs:
        notification = db.exec(
            select(Notification).where(
                Notification.recipient_uid == user.uid,
                Notification.title == title,
                Notification.related_entity_type == "competition",
                Notification.related_entity_id == competition.id,
            )
        ).first()
        if notification is None:
            notification = Notification(
                recipient_uid=user.uid,
                notification_type=NotificationType.SYSTEM,
                title=title,
                content=content,
                related_entity_type="competition",
                related_entity_id=competition.id,
                created_at=now - timedelta(hours=8),
            )
            db.add(notification)
        notification.content = content
        notification.is_read = is_read


def _refresh_counters(
    db: Session,
    soups: list[Soup],
    posts: list[Post],
    comments: list[Comment],
    tags: dict[str, Tag],
) -> None:
    db.flush()
    for soup in soups:
        scores = [
            item.score
            for item in db.exec(select(Rating).where(Rating.soup_id == soup.id)).all()
        ]
        soup.rating_count = len(scores)
        soup.avg_rating = round(sum(scores) / len(scores), 2) if scores else 0.0
        soup.like_count = len(
            db.exec(
                select(Like).where(
                    Like.target_type == LikeTargetType.SOUP,
                    Like.target_id == soup.id,
                )
            ).all()
        )
        soup.favorite_count = len(
            db.exec(
                select(Favorite).where(
                    Favorite.target_type == FavoriteTargetType.SOUP,
                    Favorite.target_id == soup.id,
                )
            ).all()
        )

    for post in posts:
        post.like_count = len(
            db.exec(
                select(Like).where(
                    Like.target_type == LikeTargetType.POST,
                    Like.target_id == post.id,
                )
            ).all()
        )
        post.favorite_count = len(
            db.exec(
                select(Favorite).where(
                    Favorite.target_type == FavoriteTargetType.POST,
                    Favorite.target_id == post.id,
                )
            ).all()
        )
        post.comment_count = len(
            db.exec(
                select(Comment).where(
                    Comment.target_type == CommentTargetType.POST,
                    Comment.target_id == post.id,
                    Comment.status == "published",
                )
            ).all()
        )

    for comment in comments:
        comment.like_count = len(
            db.exec(
                select(Like).where(
                    Like.target_type == LikeTargetType.COMMENT,
                    Like.target_id == comment.id,
                )
            ).all()
        )

    for tag in tags.values():
        tag.usage_count = len(
            db.exec(select(SoupTag).where(SoupTag.tag_id == tag.id)).all()
        )


def _database_counts(db: Session) -> dict[str, int]:
    return {
        "users": len(db.exec(select(User)).all()),
        "soups": len(db.exec(select(Soup)).all()),
        "posts": len(db.exec(select(Post)).all()),
        "comments": len(db.exec(select(Comment)).all()),
        "ratings": len(db.exec(select(Rating)).all()),
        "likes": len(db.exec(select(Like)).all()),
        "favorites": len(db.exec(select(Favorite)).all()),
        "competitions": len(db.exec(select(Competition)).all()),
        "competition_entries": len(db.exec(select(CompetitionEntry)).all()),
        "announcements": len(db.exec(select(Announcement)).all()),
    }


def seed_demo() -> dict[str, int]:
    if engine.dialect.name != "sqlite":
        raise SystemExit(
            "Refusing to seed demo data: DATABASE_URL must use SQLite."
        )

    init_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    with Session(engine) as db:
        users_by_name = _upsert_users(db, now)
        users = [users_by_name[spec["username"]] for spec in USER_SPECS]
        tags = _upsert_tags(db, now)
        collection = _upsert_collection(db, users_by_name["root"].uid, now)
        soups = _upsert_soups(db, users_by_name, tags, collection, now)
        posts = _upsert_posts(db, users_by_name, now)
        _upsert_ratings(db, users, soups, now)
        _upsert_reactions(db, users, soups, posts, now)
        comments = _upsert_comments(db, users, soups, posts, now)
        _upsert_social(db, users, now)
        _refresh_counters(db, soups, posts, comments, tags)
        competition = _upsert_competition(
            db,
            users_by_name["root"],
            tags,
            soups,
            now,
        )
        _upsert_announcement(db, users_by_name["root"], now)
        _upsert_notifications(db, users, competition, now)
        db.commit()
        counts = _database_counts(db)

    print("Demo data ready (SQLite only)")
    print(f"Root account: root / {ROOT_PASSWORD} / root@demo.example.com")
    print(f"Demo accounts: tangyuan, night_reader / {DEMO_PASSWORD}")
    print("Counts: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    return counts


if __name__ == "__main__":
    seed_demo()

# モデル定義 → 初期マイグレーション手順（M1）

目的：検索〜詳細に必要な最小テーブルを SQLAlchemy で定義し、Alembic でDBに反映する。

---

## 0. 追加するディレクトリ/ファイル

```bash
app/
├─ db.py # 既存
├─ main.py # 既存
└─ models/
├─ init.py
├─ gym.py
├─ equipment.py
├─ gym_equipment.py
├─ source.py
└─ submission.py
```

---

## 1. Base（共通）を用意（確認）

**app/db.py** に `Base = declarative_base()` があることを確認：

```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

## 2. モデル定義（最小・MVP向け）

### app/models/init.py

```python
from .gym import Gym
from .equipment import Equipment
from .gym_equipment import GymEquipment, Availability, VerificationStatus
from .source import Source, SourceType
from .submission import UserSubmission, SubmissionStatus
```

### app/models/gym.py

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db import Base

class Gym(Base):
    __tablename__ = "gyms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    chain_name = Column(String, nullable=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    address = Column(String, nullable=True)
    prefecture = Column(String, nullable=True)
    city = Column(String, nullable=True)
    official_url = Column(String, nullable=True)
    affiliate_url = Column(String, nullable=True)
    owner_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### app/models/equipment.py

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db import Base

class Equipment(Base):
    __tablename__ = "equipments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)   # 例: スクワットラック
    slug = Column(String, unique=True, nullable=False)   # 例: squat-rack
    category = Column(String, nullable=False)            # free_weight|machine|cardio|other
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### app/models/gym_equipment.py

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db import Base

class Availability(PyEnum):
    present = "present"
    absent = "absent"
    unknown = "unknown"

class VerificationStatus(PyEnum):
    unverified = "unverified"
    user_verified = "user_verified"
    owner_verified = "owner_verified"
    admin_verified = "admin_verified"

class GymEquipment(Base):
    __tablename__ = "gym_equipments"
    id = Column(Integer, primary_key=True)
    gym_id = Column(Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="CASCADE"), nullable=False)

    availability = Column(Enum(Availability), nullable=False, default=Availability.unknown)
    count = Column(Integer, nullable=True)          # 台数。不明はNULL
    max_weight_kg = Column(Integer, nullable=True)  # ダンベル最大重量など。不明はNULL
    notes = Column(String, nullable=True)

    verification_status = Column(Enum(VerificationStatus), nullable=False, default=VerificationStatus.unverified)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### app/models/source.py

```python
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db import Base

class SourceType(PyEnum):
    official_site = "official_site"
    on_site_signage = "on_site_signage"
    user_submission = "user_submission"
    media = "media"
    sns = "sns"
    other = "other"

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(Enum(SourceType), nullable=False)
    title = Column(String, nullable=True)
    url = Column(String, nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)  # 情報取得/撮影日
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### app/models/submission.py

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db import Base

class SubmissionStatus(PyEnum):
    pending = "pending"
    corroborated = "corroborated"
    approved = "approved"
    rejected = "rejected"

class UserSubmission(Base):
    __tablename__ = "user_submissions"
    id = Column(Integer, primary_key=True)
    gym_id = Column(Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="SET NULL"), nullable=True)

    payload_json = Column(String, nullable=True)  # 後でJSONに変更可
    photo_url = Column(String, nullable=True)
    visited_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.pending)
    created_by_user_id = Column(Integer, nullable=True)  # 匿名ならNULL

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

方針：不明値は NULL、同時に availability="unknown" を返す。

## 3. Alembic にモデルを認識させる

### 3-1. 初期化（未実施なら）

```bash
docker compose exec api alembic init migrations
```

### 3-2. migrations/env.py に Base とモデルを読み込ませる

```python
from app.db import Base
from app.models import gym, equipment, gym_equipment, source, submission
target_metadata = Base.metadata
```

ここがないと --autogenerate が空になります。

## 4. 初期マイグレーションを作って適用

### 4-1. 生成（差分検出）

```bash
docker compose exec api alembic revision --autogenerate -m "init schema"
```

### 4-2. 適用

```bash
docker compose exec api alembic upgrade head
```

### 4-3. 確認ポイント

Adminer（http://localhost:8080）に
gyms / equipments / gym_equipments / sources / user_submissions が作成されている

エラーが出た場合は docker compose logs -f api で確認

## 5. よくあるハマり

NoSuchModuleError: .env の DATABASE_URL が誤形式 → postgresql+psycopg2://... に修正

生成スクリプトが空: env.py でモデル未import / target_metadata 未設定

Enumの更新: Postgres Enum は追加が厳密。可能なら最初に値を十分用意

## 6. 次の一手（M1の続き）

初期データ投入（seed）

equipments 20〜30件、gyms 20件、gym_equipments は有/無/不明だけでもOK

検索API /gyms/search の実装に着手

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(String(80), nullable=False, default="xgboost")
    version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # Serialized model, stored in the database so it survives ephemeral server disks.
    artifact: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    feature_columns_json: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_production: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class MLTrainingRun(Base):
    __tablename__ = "ml_training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(String(80), nullable=False, default="xgboost")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    dataset_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    replaced_production_model: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

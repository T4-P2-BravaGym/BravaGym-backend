"""Product photos (HU-30). The file checks and the disk live in image_files (shared with T-291)."""

import logging
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.cache import invalidate_products_cache
from app.core.media import product_images_dir
from app.models import Product
from app.services.image_files import delete_image, read_image, save_image
from app.services.shop_service import get_product

logger = logging.getLogger(__name__)


def set_product_image(db: Session, product_id: int, stream: BinaryIO) -> Product:
    product = get_product(db, product_id)
    data, extension = read_image(stream)
    new_name = save_image(product_images_dir(), data, extension)

    old_name = product.image_path
    product.image_path = new_name
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_image(product_images_dir(), new_name)
        raise
    db.refresh(product)

    delete_image(product_images_dir(), old_name)
    invalidate_products_cache()
    logger.info(
        "Set photo of product %s (%s, %s bytes)", product.id, extension, len(data)
    )
    return product


def remove_product_image(db: Session, product_id: int) -> Product:
    product = get_product(db, product_id)
    old_name = product.image_path
    if old_name is None:
        return product

    product.image_path = None
    db.commit()
    db.refresh(product)

    delete_image(product_images_dir(), old_name)
    invalidate_products_cache()
    logger.info("Removed photo of product %s", product.id)
    return product

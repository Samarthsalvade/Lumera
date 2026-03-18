"""
seed_products.py — Populate the product_recommendations table.
Run once from backend/:
    python seed_products.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from models import db, ProductRecommendation

PRODUCTS = [
    # ── Cleansers ─────────────────────────────────────────────────────────────
    dict(product_name="CeraVe Foaming Facial Cleanser",
         brand="CeraVe", skin_types="oily,combination,normal",
         concerns="acne,texture,redness",
         key_ingredients="niacinamide,ceramides,hyaluronic acid",
         description="Removes excess oil without disrupting the skin barrier.",
         price_range="budget",
         url="https://www.cerave.com/facial-cleansers/foaming-facial-cleanser"),

    dict(product_name="CeraVe Hydrating Cleanser",
         brand="CeraVe", skin_types="dry,sensitive,normal",
         concerns="dryness,redness",
         key_ingredients="ceramides,hyaluronic acid,glycerin",
         description="Cream cleanser that hydrates while cleansing without stripping.",
         price_range="budget",
         url="https://www.cerave.com/facial-cleansers/hydrating-cleanser"),

    dict(product_name="La Roche-Posay Toleriane Hydrating Gentle Cleanser",
         brand="La Roche-Posay", skin_types="sensitive,dry,normal",
         concerns="redness,dryness",
         key_ingredients="niacinamide,ceramides,prebiotic thermal water",
         description="Ultra-gentle for sensitive skin, restores skin microbiome.",
         price_range="mid",
         url="https://www.laroche-posay.com"),

    # ── Toners / Essences ─────────────────────────────────────────────────────
    dict(product_name="Paula's Choice Skin Perfecting 2% BHA",
         brand="Paula's Choice", skin_types="oily,combination",
         concerns="acne,texture,hyperpigmentation",
         key_ingredients="salicylic acid,green tea extract",
         description="Exfoliating BHA toner that unclogs pores and smooths texture.",
         price_range="mid",
         url="https://www.paulaschoice.com"),

    dict(product_name="The Ordinary Glycolic Acid 7% Toning Solution",
         brand="The Ordinary", skin_types="normal,combination,dry",
         concerns="texture,hyperpigmentation,dryness",
         key_ingredients="glycolic acid,aloe vera,ginseng",
         description="AHA exfoliant that improves skin texture and radiance.",
         price_range="budget",
         url="https://theordinary.com"),

    # ── Serums ────────────────────────────────────────────────────────────────
    dict(product_name="The Ordinary Niacinamide 10% + Zinc 1%",
         brand="The Ordinary", skin_types="oily,combination,normal",
         concerns="acne,texture,hyperpigmentation,redness",
         key_ingredients="niacinamide,zinc PCA",
         description="Reduces pore appearance, controls oil, and fades blemishes.",
         price_range="budget",
         url="https://theordinary.com"),

    dict(product_name="Skinceuticals C E Ferulic",
         brand="SkinCeuticals", skin_types="normal,dry,combination",
         concerns="hyperpigmentation,texture,redness",
         key_ingredients="vitamin C,vitamin E,ferulic acid",
         description="Professional-grade antioxidant serum for brightening and protection.",
         price_range="premium",
         url="https://www.skinceuticals.com"),

    dict(product_name="The Ordinary Hyaluronic Acid 2% + B5",
         brand="The Ordinary", skin_types="dry,sensitive,normal,combination",
         concerns="dryness,redness",
         key_ingredients="hyaluronic acid,vitamin B5",
         description="Multi-depth hydration serum for all skin types.",
         price_range="budget",
         url="https://theordinary.com"),

    dict(product_name="Paula's Choice 10% Azelaic Acid Booster",
         brand="Paula's Choice", skin_types="sensitive,combination,oily",
         concerns="redness,acne,hyperpigmentation",
         key_ingredients="azelaic acid,salicylic acid,green tea",
         description="Calms redness, fights acne, and fades post-inflammatory marks.",
         price_range="mid",
         url="https://www.paulaschoice.com"),

    # ── Moisturisers ──────────────────────────────────────────────────────────
    dict(product_name="CeraVe Moisturizing Cream",
         brand="CeraVe", skin_types="dry,sensitive,normal",
         concerns="dryness,redness",
         key_ingredients="ceramides,hyaluronic acid,MVE technology",
         description="Rich barrier-repair cream for very dry and sensitive skin.",
         price_range="budget",
         url="https://www.cerave.com"),

    dict(product_name="Neutrogena Hydro Boost Water Gel",
         brand="Neutrogena", skin_types="oily,combination,normal",
         concerns="dryness,texture",
         key_ingredients="hyaluronic acid,glycerin",
         description="Lightweight gel moisturiser that hydrates without greasiness.",
         price_range="budget",
         url="https://www.neutrogena.com"),

    dict(product_name="First Aid Beauty Ultra Repair Cream",
         brand="First Aid Beauty", skin_types="dry,sensitive",
         concerns="dryness,redness,texture",
         key_ingredients="colloidal oatmeal,shea butter,ceramides",
         description="Intense hydration for severely dry and eczema-prone skin.",
         price_range="mid",
         url="https://www.firstaidbeauty.com"),

    # ── Sunscreens ────────────────────────────────────────────────────────────
    dict(product_name="EltaMD UV Clear SPF 46",
         brand="EltaMD", skin_types="oily,acne-prone,sensitive",
         concerns="acne,redness,hyperpigmentation",
         key_ingredients="zinc oxide,niacinamide,hyaluronic acid",
         description="Oil-free mineral SPF that calms redness and breakouts.",
         price_range="mid",
         url="https://eltamd.com"),

    dict(product_name="La Roche-Posay Anthelios Melt-in Milk SPF 100",
         brand="La Roche-Posay", skin_types="sensitive,normal,dry",
         concerns="redness,hyperpigmentation",
         key_ingredients="avobenzone,Cell-Ox Shield technology",
         description="High-SPF sunscreen for sensitive skin prone to burning.",
         price_range="mid",
         url="https://www.laroche-posay.com"),

    # ── Eye Creams ────────────────────────────────────────────────────────────
    dict(product_name="Kiehl's Creamy Eye Treatment with Avocado",
         brand="Kiehl's", skin_types="dry,sensitive,normal",
         concerns="dark_circles,dryness",
         key_ingredients="avocado oil,shea butter,beta-carotene",
         description="Rich eye cream that hydrates and reduces the appearance of dark circles.",
         price_range="premium",
         url="https://www.kiehls.com"),

    dict(product_name="The Inkey List Caffeine Eye Cream",
         brand="The Inkey List", skin_types="all",
         concerns="dark_circles",
         key_ingredients="caffeine,peptides,hyaluronic acid",
         description="Targets puffiness and dark circles with caffeine and peptides.",
         price_range="budget",
         url="https://www.theinkeylist.com"),

    # ── Spot Treatments ───────────────────────────────────────────────────────
    dict(product_name="Differin Adapalene Gel 0.1%",
         brand="Differin", skin_types="oily,combination",
         concerns="acne,texture,hyperpigmentation",
         key_ingredients="adapalene (retinoid)",
         description="OTC retinoid that treats and prevents acne while improving texture.",
         price_range="budget",
         url="https://www.differin.com"),

    dict(product_name="Mario Badescu Drying Lotion",
         brand="Mario Badescu", skin_types="oily,combination",
         concerns="acne",
         key_ingredients="salicylic acid,sulfur,calamine",
         description="Overnight spot treatment that dries out pimples by morning.",
         price_range="budget",
         url="https://www.mariobadescu.com"),
]


def seed():
    app = create_app()
    with app.app_context():
        existing = ProductRecommendation.query.count()
        if existing > 0:
            print(f"ℹ  {existing} products already in DB. Skipping seed.")
            print("   To reseed: delete the table first with 'DROP TABLE product_recommendations;'")
            return

        for p in PRODUCTS:
            db.session.add(ProductRecommendation(**p))
        db.session.commit()
        print(f"✅ Seeded {len(PRODUCTS)} products into product_recommendations table.")


if __name__ == '__main__':
    seed()
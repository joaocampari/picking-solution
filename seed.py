"""
Script para popular o banco de dados com a topologia fixa:
- RUA 1: 1 prateleira na esquerda (P1)
- RUA 2: 2 prateleiras (P1 esquerda, P2 direita)
- RUA 3: 1 prateleira na direita (P1)
- Cada prateleira: 24 linhas (horizontal) × 40 slots (horizontal) = 960 slots
- Total: 4 prateleiras × 960 slots = 3.840 slots
"""
from sqlalchemy.orm import Session
from models.database import SessionLocal, engine, Base
from models.aisle import Aisle
from models.shelf import Shelf
from models.slot import Slot
from services.codecs import row_to_letter


def seed_database():
    """Popula o banco com a topologia fixa"""
    # Criar todas as tabelas
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Verificar se já existe dados
        if db.query(Aisle).count() > 0:
            print("Banco já possui dados. Use --force para recriar.")
            return

        # Criar 3 Ruas
        aisles = []
        for rua_num in range(1, 4):
            aisle = Aisle(name=f"RUA {rua_num}")
            db.add(aisle)
            aisles.append(aisle)

        db.flush()  # Para obter os IDs das ruas

        # Criar prateleiras conforme topologia:
        # RUA 1: 1 prateleira na esquerda (P1)
        # RUA 2: 2 prateleiras (P1 esquerda, P2 direita)
        # RUA 3: 1 prateleira na direita (P1)
        shelves = []
        for aisle in aisles:
            rua_num = int(aisle.name.split()[-1])
            if rua_num == 1:
                # RUA 1: apenas P1 (esquerda)
                shelf = Shelf(aisle_id=aisle.id, code="P1")
                db.add(shelf)
                shelves.append(shelf)
            elif rua_num == 2:
                # RUA 2: P1 (esquerda) e P2 (direita)
                shelf1 = Shelf(aisle_id=aisle.id, code="P1")
                shelf2 = Shelf(aisle_id=aisle.id, code="P2")
                db.add(shelf1)
                db.add(shelf2)
                shelves.append(shelf1)
                shelves.append(shelf2)
            elif rua_num == 3:
                # RUA 3: apenas P1 (direita)
                shelf = Shelf(aisle_id=aisle.id, code="P1")
                db.add(shelf)
                shelves.append(shelf)

        db.flush()  # Para obter os IDs das prateleiras

        # Criar slots: 24 linhas (horizontal) × 40 slots (horizontal) por prateleira
        for shelf in shelves:
            # Extrair número da rua do nome da rua (ex: "RUA 1" -> 1)
            rua_num = shelf.aisle.name.split()[-1]
            for row in range(1, 25):  # 1..24 (linhas horizontais)
                row_letter = row_to_letter(row)
                for col in range(1, 41):  # 1..40 (slots horizontais)
                    human_code = f"R{rua_num}-{shelf.code}-{row_letter}-C{col}"
                    slot = Slot(
                        aisle_id=shelf.aisle_id,
                        shelf_id=shelf.id,
                        row_index=row,
                        col_index=col,
                        human_code=human_code,
                        occupied=False
                    )
                    db.add(slot)

        db.commit()
        total_slots = len(shelves) * 24 * 40
        print(f"✅ Seed concluído!")
        print(f"   - {len(aisles)} ruas criadas")
        print(f"   - {len(shelves)} prateleiras criadas")
        print(f"   - {total_slots} slots criados")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao fazer seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    if "--force" in sys.argv:
        # Deletar tudo e recriar
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("⚠️  Banco recriado do zero")

    seed_database()


# handlers/__init__.py — Router Registry
def register_all(dp):
    from .start import router as r0; dp.include_router(r0)
    from .admin import router as r1; dp.include_router(r1)
    from .courses import router as r2; dp.include_router(r2)
    from .subscriptions import router as r3; dp.include_router(r3)
    from .spelling import router as r4; dp.include_router(r4)
    from .placement_test import router as r5; dp.include_router(r5)
    from .exam_timer import router as r6; dp.include_router(r6)
    from .student import router as r7; dp.include_router(r7)
    from .daily_challenge import router as r8; dp.include_router(r8)
    from .writing import router as r9; dp.include_router(r9)
    from .speaking import router as r10; dp.include_router(r10)

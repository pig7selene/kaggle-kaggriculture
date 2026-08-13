"""Controlled replant-pipeline candidate factory on isolated epic copies."""

from runpy import run_path


COMMON = run_path("agents/epic_candidate_common.py")


def make_pipeline(*, pipeline=None, cows=9):
    config = {}
    if pipeline == "predictive":
        config.update({"pipeline_predictive": True, "pipeline_horizon": 3})
    elif pipeline == "chain":
        config.update({
            "pipeline_chain": True,
            "pipeline_chain_last_hour": 20,
        })
    elif pipeline == "seed_reserve":
        config.update({
            "pipeline_seed_reserve": True,
            "pipeline_seed_reserve_cap": 5,
        })
    elif pipeline == "recent_empty":
        config.update({
            "pipeline_recent_empty": True,
            "pipeline_recent_last_hour": 20,
            "pipeline_recent_radius": 3,
        })
    elif pipeline == "inventory_chain":
        config.update({
            "pipeline_inventory_chain": True,
            "pipeline_exact_chain": True,
            "pipeline_chain_last_hour": 23,
        })
    elif pipeline == "safe_exact_chain":
        config.update({
            "pipeline_inventory_chain": True,
            "pipeline_exact_chain": True,
            "pipeline_require_safe": True,
            "pipeline_chain_last_hour": 20,
        })
    elif pipeline == "opening_chain":
        # The frozen day-10 cash-return wrapper currently overrides a valid
        # stationary replant.  This flag preserves only that already-selected
        # router action; it adds no new field task.
        config.update({"pipeline_exact_chain": True})
    elif pipeline == "extended_chain":
        config.update({
            "pipeline_exact_chain": True,
            "chain_last_hour": 23,
        })
    elif pipeline == "protected_exact_chain":
        config.update({
            "pipeline_inventory_chain": True,
            "pipeline_exact_chain": True,
            "pipeline_crop_workers_only": True,
            "pipeline_global_critical_veto": True,
            "pipeline_chain_last_hour": 21,
        })
    elif pipeline == "bounded_exact_chain":
        config.update({
            "pipeline_inventory_chain": True,
            "pipeline_exact_chain": True,
            "pipeline_crop_workers_only": True,
            "pipeline_chain_last_hour": 21,
        })
    elif pipeline == "pending_chain":
        config.update({
            "pipeline_pending_chain": True,
            "pipeline_pending_horizon": 5,
            "pipeline_pending_radius": 3,
            "pipeline_phase_replant": True,
            "pipeline_chain_last_hour": 20,
        })
    elif pipeline == "cohort":
        config.update({
            "pipeline_cohort": True,
            "pipeline_cohort_size": 3,
            "cohort_priority": True,
        })
    elif pipeline == "combined":
        config.update({
            "pipeline_chain": True,
            "pipeline_chain_last_hour": 20,
            "pipeline_predictive": True,
            "pipeline_horizon": 3,
            "pipeline_cohort": True,
            "pipeline_cohort_size": 3,
            "pipeline_recent_empty": True,
            "pipeline_recent_last_hour": 20,
            "pipeline_recent_radius": 3,
            "pipeline_inventory_chain": True,
        })
    elif pipeline is not None:
        raise ValueError(pipeline)
    return COMMON["make_candidate"](cows=cows, config=config)

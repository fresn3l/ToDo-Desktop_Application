"""
Analytics Module

This module calculates comprehensive analytics and statistics:
- Overall completion statistics
- Category-based analytics
- Priority-based analytics
- Goal-based analytics
- Time-based analytics
- Productivity metrics

All functions decorated with @eel.expose are callable from JavaScript.
"""

import eel
from datetime import datetime
from typing import List, Dict

# Import data storage functions
from data_storage import load_habits, load_goals

# ============================================
# ANALYTICS FUNCTIONS
# ============================================

@eel.expose
def get_analytics():
    """
    Calculate comprehensive analytics for all habits, goals, and priorities.
    
    This function aggregates data from all habits and returns detailed statistics
    including streaks, check-ins, and consistency metrics.
    
    Returns:
        dict: Comprehensive analytics dictionary with the following structure:
            {
                "overall": {
                    "total": int,
                    "completed": int (total check-ins),
                    "incomplete": int (active habits),
                    "completion_percentage": float
                },
                "by_priority": {
                    "Now": {...},
                    "Next": {...},
                    "Later": {...}
                },
                "by_goal": {
                    "goals": {...},
                    "tasks_with_goals": int,
                    "tasks_without_goals": int,
                    "total_goals": int
                },
                "time_stats": {
                    "overdue_count": int (missed today),
                    "due_soon_count": int (active this week),
                    "completed_today": int (checked in today),
                    "created_today": int,
                    "avg_completion_days": float (avg check-ins per habit)
                },
                "productivity": {
                    "most_productive_goal": str,
                    "most_productive_completion_rate": float,
                    "goal_with_most_tasks": str,
                    "max_tasks_in_goal": int,
                    "goal_distribution": {...}
                }
            }
    
    Algorithm Overview:
        1. Load all data (habits, goals)
        2. Calculate overall statistics
        3. Group and calculate priority statistics
        4. Group and calculate goal statistics
        5. Calculate time-based metrics
        6. Calculate productivity insights
        7. Return comprehensive analytics dictionary
    """
    # ============================================
    # STEP 1: LOAD ALL DATA
    # ============================================
    # Load all data from storage files
    habits = load_habits()
    goals = load_goals()
    
    # Initialize the analytics dictionary structure
    # This will hold all calculated statistics
    analytics = {
        "overall": {},
        "by_goal": {},
        "by_priority": {},
        "time_stats": {},
        "productivity": {}
    }
    
    # ============================================
    # STEP 2: OVERALL STATISTICS
    # ============================================
    # Calculate high-level statistics across all habits
    # These give a quick overview of habit tracking
    
    total_habits = len(habits)
    # Total check-ins across all habits
    total_check_ins = sum(len(h.get("check_ins", [])) for h in habits)
    active_habits = total_habits  # All habits are active
    
    # Calculate average check-ins per habit
    avg_check_ins = (total_check_ins / total_habits) if total_habits > 0 else 0
    
    analytics["overall"] = {
        "total": total_habits,
        "completed": total_check_ins,  # Total check-ins
        "incomplete": active_habits,  # Active habits
        "completion_percentage": round(avg_check_ins, 2)  # Avg check-ins per habit
    }
    
    # ============================================
    # STEP 3: PRIORITY-BASED STATISTICS
    # ============================================
    # Group habits by priority level (Now, Next, Later) and calculate stats
    # This shows how well you're tracking high-priority habits
    
    priority_stats = {}
    priority_levels = ["Today", "Now", "Next", "Later", "Someday"]
    
    for priority in priority_levels:
        # Filter habits by this priority level
        priority_habits = [h for h in habits if h.get("priority") == priority]
        pri_total = len(priority_habits)
        pri_check_ins = sum(len(h.get("check_ins", [])) for h in priority_habits)
        pri_incomplete = pri_total  # All habits are active
        pri_percentage = (pri_check_ins / pri_total) if pri_total > 0 else 0  # Avg check-ins per habit
        
        priority_stats[priority] = {
            "total": pri_total,
            "completed": pri_check_ins,
            "incomplete": pri_incomplete,
            "completion_percentage": round(pri_percentage, 2)
        }
    
    analytics["by_priority"] = priority_stats
    
    # ============================================
    # STEP 4: GOAL-BASED STATISTICS
    # ============================================
    # Calculate statistics for each goal and habits linked to goals
    # This tracks progress toward your goals
    
    goal_stats = {}
    habits_with_goals = 0
    habits_without_goals = 0
    
    # Process each goal
    for goal in goals:
        goal_id = goal["id"]
        # Find all habits linked to this goal
        goal_habits = [h for h in habits if h.get("goal_id") == goal_id]
        goal_total = len(goal_habits)
        goal_check_ins = sum(len(h.get("check_ins", [])) for h in goal_habits)
        goal_incomplete = goal_total  # All habits are active
        goal_percentage = (goal_check_ins / goal_total) if goal_total > 0 else 0  # Avg check-ins per habit
        
        goal_stats[goal_id] = {
            "goal_name": goal.get("title", "Unknown"),
            "total": goal_total,
            "completed": goal_check_ins,
            "incomplete": goal_incomplete,
            "completion_percentage": round(goal_percentage, 2)
        }
        
        habits_with_goals += goal_total
    
    # Count habits without goals
    habits_without_goals = len([h for h in habits if not h.get("goal_id")])
    
    analytics["by_goal"] = {
        "goals": goal_stats,
        "tasks_with_goals": habits_with_goals,  # Keep key name for JS compatibility
        "tasks_without_goals": habits_without_goals,  # Keep key name for JS compatibility
        "total_goals": len(goals)
    }
    
    # ============================================
    # STEP 5: TIME-BASED STATISTICS
    # ============================================
    # Analyze habits based on check-ins and creation dates
    # This provides insights into consistency and activity patterns
    
    from datetime import date, timedelta
    now = datetime.now()
    today_str = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    
    missed_today = 0  # Habits not checked in today
    active_this_week = 0  # Habits checked in within last 7 days
    checked_in_today = 0
    created_today = 0
    total_check_ins_all = 0
    
    # Process each habit for time-based metrics
    for habit in habits:
        check_ins = habit.get("check_ins", [])
        total_check_ins_all += len(check_ins)
        
        # Check if habit was checked in today
        if today_str in check_ins:
            checked_in_today += 1
        else:
            missed_today += 1
        
        # Check if habit was active this week (checked in within last 7 days)
        if any(ci >= week_ago for ci in check_ins):
            active_this_week += 1
        
        # Check if habit was created today
        if habit.get("created_at"):
            try:
                created_at = datetime.fromisoformat(habit["created_at"])
                if created_at.date() == now.date():
                    created_today += 1
            except (ValueError, TypeError):
                pass
    
    # Calculate average check-ins per habit
    avg_check_ins_per_habit = (total_check_ins_all / len(habits)) if habits else 0
    
    analytics["time_stats"] = {
        "overdue_count": missed_today,  # Keep key name for JS compatibility
        "due_soon_count": active_this_week,  # Keep key name for JS compatibility
        "completed_today": checked_in_today,  # Keep key name for JS compatibility
        "created_today": created_today,
        "avg_completion_days": round(avg_check_ins_per_habit, 1)  # Keep key name for JS compatibility
    }
    
    # ============================================
    # STEP 6: PRODUCTIVITY METRICS
    # ============================================
    # Calculate various productivity indicators
    # These help identify patterns and areas for improvement
    
    # Find most productive goal (highest check-in rate with at least 3 habits)
    # This identifies where you're most consistent
    most_productive_goal = None
    highest_completion_rate = 0
    
    for goal_id, goal_data in goal_stats.items():
        if goal_data["total"] >= 3 and goal_data["completion_percentage"] > highest_completion_rate:
            highest_completion_rate = goal_data["completion_percentage"]
            most_productive_goal = goal_data["goal_name"]
    
    # Find goal with most habits
    # This shows where you focus most of your effort
    goal_with_most_tasks = None
    max_tasks = 0
    for goal_id, goal_data in goal_stats.items():
        if goal_data["total"] > max_tasks:
            max_tasks = goal_data["total"]
            goal_with_most_tasks = goal_data["goal_name"]
    
    # Calculate habit distribution (percentage of habits in each goal)
    # This shows how habits are distributed across goals
    goal_distribution = {}
    for goal_id, goal_data in goal_stats.items():
        if total_habits > 0:
            goal_distribution[goal_data["goal_name"]] = round((goal_data["total"] / total_habits * 100), 2)
        else:
            goal_distribution[goal_data["goal_name"]] = 0
    
    analytics["productivity"] = {
        "most_productive_goal": most_productive_goal,
        "most_productive_completion_rate": round(highest_completion_rate, 2) if most_productive_goal else 0,
        "goal_with_most_tasks": goal_with_most_tasks,
        "max_tasks_in_goal": max_tasks,
        "goal_distribution": goal_distribution
    }
    
    # ============================================
    # STEP 8: RETURN ANALYTICS
    # ============================================
    # Return the complete analytics dictionary
    # This will be sent to JavaScript for display
    return analytics


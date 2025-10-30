"""
PREY workflow tasks for crew execution.

Defines tasks for each phase of the PREY loop.
"""

from textwrap import dedent
from crewai import Task


def create_perceive_task(agent, mission_context: str) -> Task:
    """Create Perceive task.
    
    Args:
        agent: Perceiver agent
        mission_context: Mission context and instructions
        
    Returns:
        Configured perceive task
    """
    return Task(
        description=dedent(f"""
            Scan the repository and gather context for this mission:
            
            {mission_context}
            
            Your responsibilities:
            1. Read the mission intent and understand objectives
            2. Identify relevant files and current state
            3. Note constraints, safety limits, and targets
            4. Capture any existing issues or blockers
            5. Document findings clearly for the Reactor
            
            Do NOT make any changes. Only observe and report.
        """).strip(),
        agent=agent,
        expected_output="Detailed perception report with context, constraints, and findings"
    )


def create_react_task(agent, perceive_output: str = "") -> Task:
    """Create React task.
    
    Args:
        agent: Reactor agent
        perceive_output: Output from perceive phase (optional)
        
    Returns:
        Configured react task
    """
    context_note = f"\n\nPerception findings:\n{perceive_output}" if perceive_output else ""
    
    return Task(
        description=dedent(f"""
            Analyze the perception findings and create an execution plan.
            {context_note}
            
            Your responsibilities:
            1. Classify the domain and complexity
            2. Choose the appropriate approach
            3. Plan chunk sizes (≤200 lines per chunk)
            4. Define safety tripwires
            5. Create step-by-step execution plan
            6. Identify success criteria
            
            Ensure the plan respects all safety constraints.
        """).strip(),
        agent=agent,
        expected_output="Detailed execution plan with chunks, tripwires, and steps"
    )


def create_engage_task(agent, plan: str = "") -> Task:
    """Create Engage task.
    
    Args:
        agent: Engager agent
        plan: Execution plan from react phase (optional)
        
    Returns:
        Configured engage task
    """
    plan_note = f"\n\nExecution plan:\n{plan}" if plan else ""
    
    return Task(
        description=dedent(f"""
            Execute the planned work safely and precisely.
            {plan_note}
            
            Your responsibilities:
            1. Follow the execution plan exactly
            2. Make minimal, surgical changes only
            3. Respect chunk limits (≤200 lines per write)
            4. Check tripwires after each chunk
            5. Log all material actions
            6. Stop immediately if any tripwire triggers
            
            Quality and safety are paramount.
        """).strip(),
        agent=agent,
        expected_output="Completed work with evidence of changes and safety checks"
    )


def create_yield_task(agent, work_output: str = "") -> Task:
    """Create Yield task.
    
    Args:
        agent: Yielder agent
        work_output: Output from engage phase (optional)
        
    Returns:
        Configured yield task
    """
    work_note = f"\n\nWork completed:\n{work_output}" if work_output else ""
    
    return Task(
        description=dedent(f"""
            Assemble all work outputs into a review bundle.
            {work_note}
            
            Your responsibilities:
            1. Collect all artifacts created
            2. Gather evidence references (files, lines, hashes)
            3. Compile safety check results
            4. Package blackboard receipts
            5. Create clear summary for verification
            
            Ensure nothing is missing from the bundle.
        """).strip(),
        agent=agent,
        expected_output="Complete review bundle with artifacts, evidence, and receipts"
    )


def create_verify_task(agent, bundle: str = "", agent_role: str = "") -> Task:
    """Create Verify task for validators.
    
    Args:
        agent: Validator agent (immunizer, disruptor, or verifier_aux)
        bundle: Review bundle from yield phase (optional)
        agent_role: Specific role perspective for validation
        
    Returns:
        Configured verify task
    """
    bundle_note = f"\n\nReview bundle:\n{bundle}" if bundle else ""
    role_context = f" from {agent_role} perspective" if agent_role else ""
    
    return Task(
        description=dedent(f"""
            Verify the submitted work{role_context}.
            {bundle_note}
            
            Your responsibilities:
            1. Check for safety violations
            2. Verify chunk limits respected
            3. Scan for placeholders
            4. Validate evidence completeness
            5. Test for edge cases and weaknesses
            6. Provide clear PASS/FAIL verdict
            
            Be thorough and uncompromising on quality.
        """).strip(),
        agent=agent,
        expected_output="Verification report with PASS/FAIL verdict and findings"
    )

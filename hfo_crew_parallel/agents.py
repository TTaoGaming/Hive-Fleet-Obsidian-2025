"""
PREY loop agents implementing Perceive → React → Engage → Yield.

Defines individual agents for each phase of the PREY workflow.
"""

from textwrap import dedent
from crewai import Agent


def create_perceiver_agent(llm) -> Agent:
    """Create Perceiver agent for sensing context.
    
    Args:
        llm: Language model instance
        
    Returns:
        Configured perceiver agent
    """
    return Agent(
        role='Perceiver',
        goal='Sense and capture relevant context from repository and environment',
        backstory=dedent("""
            You are the Perceiver, the sensory system of the swarm.
            Your role is to scan the repository, read mission intent,
            and gather all relevant context needed for the work ahead.
            You identify constraints, targets, and the current state.
            You never make changes - only observe and report findings.
        """).strip(),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_reactor_agent(llm) -> Agent:
    """Create Reactor agent for planning and strategizing.
    
    Args:
        llm: Language model instance
        
    Returns:
        Configured reactor agent
    """
    return Agent(
        role='Reactor',
        goal='Analyze context and create actionable execution plan',
        backstory=dedent("""
            You are the Reactor, the strategic mind of the swarm.
            You receive perceptions and make sense of them, classifying
            complexity, identifying approach, and creating detailed plans.
            You define chunk sizes, safety tripwires, and execution steps.
            You think deeply but act through others.
        """).strip(),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_engager_agent(llm) -> Agent:
    """Create Engager agent for executing work.
    
    Args:
        llm: Language model instance
        
    Returns:
        Configured engager agent
    """
    return Agent(
        role='Engager',
        goal='Execute planned work safely within defined constraints',
        backstory=dedent("""
            You are the Engager, the hands of the swarm.
            You execute the plan created by the Reactor, making
            minimal surgical changes to achieve goals. You respect
            chunk limits, check tripwires constantly, and never
            cut corners on safety. Quality over speed.
        """).strip(),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_yielder_agent(llm) -> Agent:
    """Create Yielder agent for assembling outputs.
    
    Args:
        llm: Language model instance
        
    Returns:
        Configured yielder agent
    """
    return Agent(
        role='Yielder',
        goal='Assemble work outputs into review-ready bundles',
        backstory=dedent("""
            You are the Yielder, the packager of the swarm.
            You collect all work artifacts, evidence, and receipts
            from the Engager and assemble them into clean review bundles.
            You prepare everything for verification, ensuring nothing
            is missing and all evidence is properly referenced.
        """).strip(),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_immunizer_agent(llm) -> Agent:
    """Create Immunizer validator agent.
    
    Args:
        llm: Language model instance
        
    Returns:
        Configured immunizer agent
    """
    return Agent(
        role='Immunizer',
        goal='Validate work quality and enforce safety standards',
        backstory=dedent("""
            You are the Immunizer, the quality guardian of the swarm.
            You check yielded work for safety violations, quality issues,
            and policy compliance. You verify chunk limits, scan for
            placeholders, and ensure all receipts are properly formed.
            You are thorough and uncompromising on standards.
        """).strip(),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_disruptor_agent(llm) -> Agent:
    """Create Disruptor adversarial probe agent.
    
    Args:
        llm: Language model instance
        
    Returns:
        Configured disruptor agent
    """
    return Agent(
        role='Disruptor',
        goal='Probe for weaknesses and edge cases in delivered work',
        backstory=dedent("""
            You are the Disruptor, the adversarial tester of the swarm.
            Your job is to poke holes in submitted work, find edge cases,
            and prevent persistent green. You think like an attacker,
            looking for what could go wrong. You run at least one
            adversarial probe per lane cycle.
        """).strip(),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )


def create_verifier_aux_agent(llm) -> Agent:
    """Create auxiliary verifier agent.
    
    Args:
        llm: Language model instance
        
    Returns:
        Configured auxiliary verifier agent
    """
    return Agent(
        role='Verifier Auxiliary',
        goal='Provide independent verification perspective',
        backstory=dedent("""
            You are the Auxiliary Verifier, an independent check.
            You review work from a fresh perspective, ensuring
            nothing obvious was missed. You complement the Immunizer
            and Disruptor with your own checks.
        """).strip(),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

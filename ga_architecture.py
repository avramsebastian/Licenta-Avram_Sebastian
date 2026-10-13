from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from settings import Settings
from ga_models import Genome

class GenomeArchitectureStrategy(ABC):
    """
    Abstract base class defining the strategy for genome architecture management.
    """
    __slots__ = ()

    @abstractmethod
    def get_initial_length(self) -> int:
        """
        Retrieves the initial length of the genome for the first generation.

        Returns:
            int: The starting number of genes for new agents.
        """
        pass

    @abstractmethod
    def handle_exhaustion(self, parent_genomes: List[Genome]) -> bool:
        """
        Invoked when the agents exhausts its current search space.
        
        Args:
            parent_genomes (List[Genome]): The current population of genomes to potentially modify.

        Returns:
            bool: True if the architecture was modified, False otherwise.
        """
        pass

class StaticGenomeArchitecture(GenomeArchitectureStrategy):
    """
    Strategy for Phase 1: A static genome architecture.
    Genomes start at their full length and do not grow upon exhaustion.
    """
    __slots__ = ()

    def get_initial_length(self) -> int:
        """
        Retrieves the standard fixed genome length for Phase 1.

        Returns:
            int: The full static length defined in Settings (GA_GENOME_LENGTH).
        """
        return Settings.GA_GENOME_LENGTH

    def handle_exhaustion(self, parent_genomes: List[Genome]) -> bool:
        """
        Handles exhaustion for a static architecture. 
        In Phase 1, the genome length is fixed, so no genes are appended. 
        The algorithm will only rely on mutation reheating.

        Args:
            parent_genomes (List[Genome]): The current population of genomes.

        Returns:
            bool: Always returns False, indicating no structural growth occurred.
        """
        return False

class ProgressiveGenomeArchitecture(GenomeArchitectureStrategy):
    """
    Strategy for Phase 2: A progressive genome growth architecture.
    Genomes start short and expand their capacity when the 
    current structural configuration is fully exhausted and cannot improve anymore.
    """
    __slots__ = ()

    def get_initial_length(self) -> int:
        """
        Retrieves the starting genome length for Phase 2.

        Returns:
            int: The starting length defined in Settings (GA_PROGRESSIVE_START_LENGTH).
        """
        return Settings.GA_PROGRESSIVE_START_LENGTH

    def handle_exhaustion(self, parent_genomes: List[Genome]) -> bool:
        """
        Appends a fixed number of new randomized genes to every genome in the population.

        Args:
            parent_genomes (List[Genome]): The current population of genomes to be expanded.

        Returns:
            bool: Always returns True, indicating structural growth occurred.
        """
        growth_amount = Settings.GA_PROGRESSIVE_GROWTH_AMOUNT
        print(f"Exhaustion reached! Expanding Genome by +{growth_amount} genes.")
        
        for g in parent_genomes:
            g.append_genes(growth_amount)
            
        return True

class GenomeArchitectureFactory:
    """
    Factory class responsible for instantiating the correct GenomeArchitectureStrategy
    based on the current phase flag in the configuration settings.
    """
    __slots__ = ()

    _progressive_instance = None
    _static_instance = None

    @classmethod
    def create(cls) -> GenomeArchitectureStrategy:
        """
        Creates and returns the appropriate architecture strategy.

        Returns:
            GenomeArchitectureStrategy: An instance of ProgressiveGenomeArchitecture 
                                        if GA_ALLOW_PROGRESSIVE_GROWTH is True, 
                                        otherwise StaticGenomeArchitecture.
        """
        if Settings.GA_ALLOW_PROGRESSIVE_GROWTH:
            if cls._progressive_instance is None:
                cls._progressive_instance = ProgressiveGenomeArchitecture()
            return cls._progressive_instance
            
        if cls._static_instance is None:
            cls._static_instance = StaticGenomeArchitecture()
        return cls._static_instance
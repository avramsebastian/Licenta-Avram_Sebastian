from __future__ import annotations
from settings import Settings
from random import uniform, choice, random, randint, gauss, sample
from dataclasses import dataclass, field
from typing import List, Tuple, Dict

# Jump and walk action boundary dictionary defining (min, max) strength intervals
JUMP_BOUNDS: Dict[str, Tuple[float, float]] = {
    "JUMP_LOW": (3.0, 6.0),
    "JUMP_MEDIUM": (15.0, 20.0),
    "JUMP_HIGH": (25.0, 30.0),
    "WALK": (20.0, 40.0)
}


@dataclass
class Gene:
    """
    Represents an action type, a horizontal direction, and an action strength.
    """
    action_type: str
    direction: int
    strength: float

    @staticmethod
    def random_gene() -> Gene:
        """
        Generates a new random Gene instance with randomly selected action type,
        direction (-1 or 1), and strength sampled within interval bounds.

        Args:
            None

        Returns:
            Gene: A newly instantiated random Gene.
        """
        action_type = choice(["JUMP_LOW", "JUMP_MEDIUM", "JUMP_HIGH", "WALK"])
        direction = choice([-1, 1])
        min_s, max_s = JUMP_BOUNDS[action_type]
        strength = uniform(min_s, max_s)
        return Gene(action_type=action_type, direction=direction, strength=strength)

    def mutate(
        self, 
        mutation_rate_dir:float,
        mutation_rate_type:float,
        mutation_rate_strength:float,
        sigma,
    ) -> None:
        """
        Applies independent mutations to direction, action type, and strength.
        - Direction: Random reset to -1 or 1 with probability mutation_rate_dir.
        - Action Type: Random transition to another action type with probability mutation_rate_type.
        - Strength: Gaussian perturbation bounded within action type interval with probability mutation_rate_strength.

        Args:
            mutation_rate_dir (float): Probability of mutating horizontal direction. 
            mutation_rate_type (float): Probability of mutating action type.
            mutation_rate_strength (float): Probability of perturbing strength value. 
            sigma (float): Standard deviation of Gaussian perturbation. 

        Returns:
            None
        """

        if random() < mutation_rate_dir:
            self.direction = choice([-1, 1])

        if random() < mutation_rate_type:
            types = ["JUMP_LOW", "JUMP_MEDIUM", "JUMP_HIGH", "WALK"]
            if self.action_type in types:
                types.remove(self.action_type)
            self.action_type = choice(types)

            min_s, max_s = JUMP_BOUNDS[self.action_type]
            self.strength = uniform(min_s, max_s)

        if random() < mutation_rate_strength:
            min_s, max_s = JUMP_BOUNDS[self.action_type]
            bracket_width = max_s - min_s
            scaled_sigma = sigma * bracket_width

            delta = gauss(0, scaled_sigma)
            new_strength = self.strength + delta

            self.strength = max(min_s, min(max_s, new_strength))


@dataclass
class Genome:
    """
    Container for a sequence of Genes.
    """
    genes: List[Gene] = field(default_factory=list)

    @staticmethod
    def random_genome(length: int) -> Genome:
        """
        Generates a new Genome containing a specified number of random Genes.

        Args:
            length (int): Number of genes in the initial sequence.

        Returns:
            Genome: A newly instantiated random Genome.
        """
        return Genome(genes=[Gene.random_gene() for _ in range(length)])

    def crossover(self, partner: Genome, crossover_rate: float) -> Tuple[Genome, Genome]:
        """
        Performs 1-point crossover between this genome and a partner genome.

        Args:
            partner (Genome): The partner Genome instance for crossover.
            crossover_rate (float): Probability of performing crossover.

        Returns:
            Tuple[Genome, Genome]: Two offspring Genome instances.
        """
        min_len = min(len(self.genes), len(partner.genes))
        if random() > crossover_rate or min_len < 2:
            return (
                Genome(genes=[Gene(g.action_type, g.direction, g.strength) for g in self.genes]),
                Genome(genes=[Gene(g.action_type, g.direction, g.strength) for g in partner.genes])
            )

        cut = randint(2, min_len // 2 - 1)

        child1_genes = [
            Gene(g.action_type, g.direction, g.strength)
            for g in self.genes[:cut] + partner.genes[cut:]
        ]
        child2_genes = [
            Gene(g.action_type, g.direction, g.strength)
            for g in partner.genes[:cut] + self.genes[cut:]
        ]

        return (Genome(genes=child1_genes), Genome(genes=child2_genes))

    def mutate(
        self, 
        mutation_rate_dir:float,
        mutation_rate_type:float, 
        mutation_rate_strength:float,
        sigma,
    ) -> None:
        """
        Applies mutation across all genes uniformly.

        Args:
            mutation_rate_dir (float): Base probability of mutating direction. 
            mutation_rate_type (float): Base probability of mutating action type. 
            mutation_rate_strength (float): Base probability of perturbing strength.
            sigma (float): Standard deviation for Gaussian perturbation. 

        Returns:
            None
        """
        for gene in self.genes:
            gene.mutate(
                mutation_rate_dir,
                mutation_rate_type,
                mutation_rate_strength,
                sigma
            )

    def append_genes(self, count: int) -> None:
        """
        Appends new random genes to the end of the genome (Progressive Genome Growth).

        Args:
            count (int): Number of new random genes to append.

        Returns:
            None
        """
        for _ in range(count):
            self.genes.append(Gene.random_gene())

"""
Immune Trajectory Prediction Model Prototype
=============================================

Multi-task Temporal Fusion Transformer (TFT) for predicting immune disease
risk scores across 7 diseases and 4 time horizons.

Project: Digital Columbus - Immune Care Ontology R&D
Architecture: Variable Selection Network + LSTM Encoder + Ontology-Informed
              Attention + Multi-task Disease Heads

Usage:
    python3 model_prototype.py

This script validates the model architecture by running a forward pass
with dummy data and printing output shapes.
"""

import math
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_DISEASES: int = 7
NUM_HORIZONS: int = 4
DISEASE_NAMES: List[str] = [
    "atopic_dermatitis",  # L20
    "asthma",             # J45
    "allergic_rhinitis",  # J30
    "psoriasis",          # L40
    "dry_eye",            # H04.1
    "rheumatoid_arthritis",
    "alopecia",
]
HORIZON_NAMES: List[str] = ["1day", "1week", "1month", "3month"]

# Feature dimensions per layer
LAYER_DIMS: Dict[str, int] = {
    "environment": 30,
    "composite": 15,
    "lifelog": 20,
    "biomarker": 15,
    "treatment": 6,
    "external": 10,
    "cross": 10,
}
STATIC_DIM: int = 8
TOTAL_TIME_VARYING_DIM: int = sum(LAYER_DIMS.values())  # 106
# With static covariates broadcast: 106 time-varying + 8 static = 114 input


# ---------------------------------------------------------------------------
# Gated Residual Network (GRN)
# ---------------------------------------------------------------------------

class GatedResidualNetwork(nn.Module):
    """Gated Residual Network used throughout the TFT architecture.

    Applies a gated skip connection with optional context vector injection.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        context_dim: Optional[int] = None,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim

        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.elu = nn.ELU()
        self.fc2 = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(dropout)

        if context_dim is not None:
            self.context_proj = nn.Linear(context_dim, hidden_dim, bias=False)
        else:
            self.context_proj = None

        # Gating layer
        self.gate = nn.Linear(output_dim, output_dim)
        self.layer_norm = nn.LayerNorm(output_dim)

        # Skip connection projection if dimensions differ
        if input_dim != output_dim:
            self.skip_proj = nn.Linear(input_dim, output_dim)
        else:
            self.skip_proj = None

    def forward(
        self,
        x: torch.Tensor,
        context: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Input tensor of shape (..., input_dim).
            context: Optional context vector of shape (..., context_dim).

        Returns:
            Output tensor of shape (..., output_dim).
        """
        residual = x if self.skip_proj is None else self.skip_proj(x)

        hidden = self.fc1(x)
        if self.context_proj is not None and context is not None:
            hidden = hidden + self.context_proj(context)
        hidden = self.elu(hidden)
        hidden = self.fc2(hidden)
        hidden = self.dropout(hidden)

        # Gated linear unit
        gate_values = torch.sigmoid(self.gate(hidden))
        hidden = gate_values * hidden

        # Add & norm
        output = self.layer_norm(hidden + residual)
        return output


# ---------------------------------------------------------------------------
# Variable Selection Network (VSN)
# ---------------------------------------------------------------------------

class VariableSelectionNetwork(nn.Module):
    """Selects important features within a single data layer.

    Each layer (environment, lifelog, biomarker, etc.) has its own VSN that
    learns feature-level attention weights. Static covariates are injected
    as context to enable patient-specific feature selection.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        static_dim: int,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # Per-feature GRN transforms
        self.feature_grns = nn.ModuleList([
            GatedResidualNetwork(1, hidden_dim, hidden_dim, context_dim=static_dim, dropout=dropout)
            for _ in range(input_dim)
        ])

        # Softmax attention over features
        self.attention_grn = GatedResidualNetwork(
            input_dim * hidden_dim, hidden_dim, input_dim,
            context_dim=static_dim, dropout=dropout,
        )

    def forward(
        self,
        x: torch.Tensor,
        static_context: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Select important features from input.

        Args:
            x: Input of shape (batch, seq_len, input_dim).
            static_context: Static covariates of shape (batch, static_dim),
                broadcast across time steps.

        Returns:
            selected: Weighted feature combination (batch, seq_len, hidden_dim).
            weights: Feature attention weights (batch, seq_len, input_dim).
        """
        batch_size, seq_len, _ = x.shape

        # Expand static context for time dimension
        ctx = static_context.unsqueeze(1).expand(-1, seq_len, -1)  # (B, T, static_dim)

        # Transform each feature independently
        transformed = []
        for i, grn in enumerate(self.feature_grns):
            feat_i = x[:, :, i : i + 1]  # (B, T, 1)
            transformed.append(grn(feat_i, ctx))  # (B, T, hidden_dim)

        # Stack: (B, T, input_dim, hidden_dim)
        transformed = torch.stack(transformed, dim=2)

        # Compute attention weights
        flat = transformed.reshape(batch_size, seq_len, -1)  # (B, T, input_dim * hidden_dim)
        attention_logits = self.attention_grn(flat, ctx)  # (B, T, input_dim)
        weights = F.softmax(attention_logits, dim=-1)  # (B, T, input_dim)

        # Weighted sum of transformed features
        # weights: (B, T, input_dim, 1), transformed: (B, T, input_dim, hidden_dim)
        selected = (weights.unsqueeze(-1) * transformed).sum(dim=2)  # (B, T, hidden_dim)

        return selected, weights


# ---------------------------------------------------------------------------
# Temporal Encoder
# ---------------------------------------------------------------------------

class TemporalEncoder(nn.Module):
    """LSTM-based temporal encoder with gated residual connections.

    Encodes time-series patterns from the concatenated selected features
    of all layers.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # Project bidirectional output back to hidden_dim
        self.projection = nn.Linear(hidden_dim * 2, hidden_dim)
        self.grn = GatedResidualNetwork(hidden_dim, hidden_dim, hidden_dim, dropout=dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode temporal patterns.

        Args:
            x: Input of shape (batch, seq_len, input_dim).

        Returns:
            Encoded sequence of shape (batch, seq_len, hidden_dim).
        """
        lstm_out, _ = self.lstm(x)  # (B, T, hidden*2)
        projected = self.projection(lstm_out)  # (B, T, hidden)
        encoded = self.grn(projected)  # (B, T, hidden)
        return encoded


# ---------------------------------------------------------------------------
# Ontology-Informed Attention Prior
# ---------------------------------------------------------------------------

class OntologyAttentionPrior(nn.Module):
    """Incorporates causal pathway knowledge as attention bias.

    Loads known causal relationships from the ontology and constructs an
    attention bias matrix that encourages the model to attend to
    established causal pathways.
    """

    def __init__(
        self,
        num_features: int,
        num_heads: int = 4,
        tau: float = 1.0,
    ) -> None:
        super().__init__()
        self.num_features = num_features
        self.num_heads = num_heads
        self.tau = tau

        # Learnable bias matrix initialized from ontology priors
        # Shape: (num_heads, num_features, num_features)
        self.bias = nn.Parameter(torch.zeros(num_heads, num_features, num_features))

        # Initialize with known causal pathways
        self._initialize_ontology_priors()

    def _initialize_ontology_priors(self) -> None:
        """Initialize attention bias from known causal pathways.

        In production, this would query SPARQL endpoint for CausalPathway
        instances. Here we hardcode key known relationships.
        """
        # Known causal correlations from domain_analysis.md
        # Format: (upstream_feature_idx, downstream_feature_idx, correlation)
        known_pathways = [
            # PM2.5 -> IL-6 (r=0.52, Head 0: env->bio)
            (0, 66, 0.52),
            # VOC -> IgE (r=0.35, Head 0: env->bio)
            (7, 72, 0.35),
            # Humidity -> IL-13 via allergen (r=0.30, Head 0: env->bio)
            (14, 71, 0.30),
            # HRV -> IL-6 (r=-0.42, Head 1: lifelog->bio)
            (46, 66, -0.42),
            # SpO2 -> CRP (r=-0.35, Head 1: lifelog->bio)
            (50, 74, -0.35),
            # Sleep -> TNF-alpha (r=-0.38, Head 1: lifelog->bio)
            (52, 68, -0.38),
            # Activity -> TNF-alpha (r=-0.28, Head 1: lifelog->bio)
            (56, 68, -0.28),
            # Skin temp -> circadian (r=0.31, Head 1: lifelog->bio)
            (59, 68, 0.31),
        ]

        with torch.no_grad():
            for upstream, downstream, corr in known_pathways:
                if upstream < self.num_features and downstream < self.num_features:
                    # Assign to appropriate head based on pathway type
                    head = 0 if upstream < 45 else 1  # env->bio vs lifelog->bio
                    self.bias.data[head, upstream, downstream] = abs(corr)

    def get_attention_bias(self, seq_len: int) -> torch.Tensor:
        """Generate attention bias for a given sequence length.

        The feature-level bias is applied uniformly across time steps.
        In a full implementation, temporal lag information would modulate
        the bias at specific time offsets.

        Args:
            seq_len: Length of the temporal sequence.

        Returns:
            Bias tensor of shape (num_heads, seq_len, seq_len) for
            temporal attention, derived from feature-level priors.
        """
        # For temporal attention, we create a simple decaying bias
        # that reflects the ontology structure
        # Mean bias strength across feature pairs
        bias_strength = self.bias.abs().mean(dim=(1, 2))  # (num_heads,)

        # Create temporal bias: nearby time steps get stronger bias
        positions = torch.arange(seq_len, device=self.bias.device, dtype=torch.float)
        time_diff = (positions.unsqueeze(0) - positions.unsqueeze(1)).abs()
        # Exponential decay based on temporal distance
        temporal_bias = torch.exp(-time_diff / max(seq_len * 0.3, 1.0))

        # Scale by ontology-derived bias strength per head
        # (num_heads, 1, 1) * (seq_len, seq_len) -> (num_heads, seq_len, seq_len)
        attention_bias = bias_strength.view(-1, 1, 1) * temporal_bias.unsqueeze(0)

        return attention_bias / self.tau


# ---------------------------------------------------------------------------
# Multi-Head Interpretable Attention
# ---------------------------------------------------------------------------

class InterpretableMultiHeadAttention(nn.Module):
    """Multi-head attention with ontology-informed priors.

    Each head specializes in a different causal pathway type:
      - Head 0: Environment -> Biomarker pathways
      - Head 1: Lifelog -> Biomarker pathways
      - Head 2: Treatment -> Biomarker pathways
      - Head 3: Free attention (data-driven)
    """

    def __init__(
        self,
        d_model: int,
        num_heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        assert d_model % num_heads == 0, "d_model must be divisible by num_heads"

        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)

        self.dropout = nn.Dropout(dropout)
        self.layer_norm = nn.LayerNorm(d_model)

    def forward(
        self,
        x: torch.Tensor,
        attention_bias: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute multi-head attention with optional ontology bias.

        Args:
            x: Input of shape (batch, seq_len, d_model).
            attention_bias: Optional bias of shape (num_heads, seq_len, seq_len).

        Returns:
            output: Attended output (batch, seq_len, d_model).
            attention_weights: Attention weights (batch, num_heads, seq_len, seq_len).
        """
        batch_size, seq_len, _ = x.shape

        # Linear projections
        Q = self.W_q(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        K = self.W_k(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        V = self.W_v(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)

        # Scaled dot-product attention
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)

        # Add ontology-informed attention bias
        if attention_bias is not None:
            # Expand bias for batch dimension: (1, num_heads, seq_len, seq_len)
            scores = scores + attention_bias.unsqueeze(0)

        attention_weights = F.softmax(scores, dim=-1)
        attention_weights = self.dropout(attention_weights)

        # Apply attention to values
        context = torch.matmul(attention_weights, V)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)

        # Output projection + residual
        output = self.layer_norm(self.W_o(context) + x)

        return output, attention_weights


# ---------------------------------------------------------------------------
# Multi-Task Disease Head
# ---------------------------------------------------------------------------

class MultiTaskHead(nn.Module):
    """Multi-task prediction heads for disease risk scores.

    Predicts risk scores for 7 diseases across 4 time horizons.
    Also outputs an overall Immune Risk Score (0-100).
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_diseases: int = NUM_DISEASES,
        num_horizons: int = NUM_HORIZONS,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()
        self.num_diseases = num_diseases
        self.num_horizons = num_horizons

        # Per-horizon shared layer
        self.horizon_layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
            for _ in range(num_horizons)
        ])

        # Per-disease output layers (shared across horizons for parameter efficiency)
        self.disease_layers = nn.ModuleList([
            nn.Linear(hidden_dim, 1)
            for _ in range(num_diseases)
        ])

        # Overall immune risk score head
        self.immune_risk_head = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Predict disease risk scores.

        Args:
            x: Aggregated temporal representation (batch, input_dim).
                Typically the last time step or pooled output from the encoder.

        Returns:
            disease_risks: Risk scores (batch, num_horizons, num_diseases).
                          Values in [0, 1] via sigmoid.
            immune_risk: Overall immune risk score (batch, 1). Values in [0, 100].
        """
        all_horizon_risks = []

        for h_idx, horizon_layer in enumerate(self.horizon_layers):
            horizon_repr = horizon_layer(x)  # (B, hidden_dim)
            disease_logits = []
            for d_idx, disease_layer in enumerate(self.disease_layers):
                logit = disease_layer(horizon_repr)  # (B, 1)
                disease_logits.append(logit)
            # (B, num_diseases)
            horizon_risks = torch.sigmoid(torch.cat(disease_logits, dim=-1))
            all_horizon_risks.append(horizon_risks)

        # Stack: (B, num_horizons, num_diseases)
        disease_risks = torch.stack(all_horizon_risks, dim=1)

        # Overall immune risk score (0-100 scale)
        immune_risk = torch.sigmoid(self.immune_risk_head(x)) * 100.0  # (B, 1)

        return disease_risks, immune_risk


# ---------------------------------------------------------------------------
# Static Covariate Encoder
# ---------------------------------------------------------------------------

class StaticCovariateEncoder(nn.Module):
    """Encodes static patient covariates (age, sex, BMI, etc.).

    Produces context vectors used by Variable Selection Networks and
    other components to enable patient-specific behavior.
    """

    def __init__(
        self,
        static_dim: int,
        hidden_dim: int,
        num_contexts: int = 4,
    ) -> None:
        super().__init__()
        self.encoders = nn.ModuleList([
            GatedResidualNetwork(static_dim, hidden_dim, hidden_dim)
            for _ in range(num_contexts)
        ])

    def forward(self, static: torch.Tensor) -> List[torch.Tensor]:
        """Encode static covariates into multiple context vectors.

        Args:
            static: Static features of shape (batch, static_dim).

        Returns:
            List of context vectors, each of shape (batch, hidden_dim).
        """
        return [encoder(static) for encoder in self.encoders]


# ---------------------------------------------------------------------------
# Full Model: ImmuneTrajectoryModel
# ---------------------------------------------------------------------------

class ImmuneTrajectoryModel(nn.Module):
    """Multi-task Temporal Fusion Transformer for immune trajectory prediction.

    Integrates 4-layer time-series features (environment, lifelog, biomarker,
    treatment) with ontology-informed attention priors to predict 7 disease
    risk scores across 4 time horizons.
    """

    def __init__(
        self,
        layer_dims: Optional[Dict[str, int]] = None,
        static_dim: int = STATIC_DIM,
        hidden_dim: int = 128,
        attention_heads: int = 4,
        lstm_layers: int = 2,
        dropout: float = 0.1,
        head_dropout: float = 0.3,
        ontology_tau: float = 1.0,
    ) -> None:
        super().__init__()

        if layer_dims is None:
            layer_dims = LAYER_DIMS

        self.layer_dims = layer_dims
        self.hidden_dim = hidden_dim
        total_tv_dim = sum(layer_dims.values())

        # 1. Static Covariate Encoder
        self.static_encoder = StaticCovariateEncoder(static_dim, hidden_dim)

        # 2. Variable Selection Networks (one per layer)
        self.vsn_modules = nn.ModuleDict()
        for layer_name, dim in layer_dims.items():
            self.vsn_modules[layer_name] = VariableSelectionNetwork(
                input_dim=dim,
                hidden_dim=hidden_dim,
                static_dim=hidden_dim,  # context from static encoder
                dropout=dropout,
            )

        # 3. Temporal Encoder
        num_layers = len(layer_dims)
        self.temporal_encoder = TemporalEncoder(
            input_dim=hidden_dim * num_layers,  # concatenated VSN outputs
            hidden_dim=hidden_dim,
            num_layers=lstm_layers,
            dropout=dropout,
        )

        # 4. Ontology Attention Prior
        self.ontology_prior = OntologyAttentionPrior(
            num_features=total_tv_dim,
            num_heads=attention_heads,
            tau=ontology_tau,
        )

        # 5. Interpretable Multi-Head Attention
        self.attention = InterpretableMultiHeadAttention(
            d_model=hidden_dim,
            num_heads=attention_heads,
            dropout=dropout,
        )

        # 6. Multi-Task Disease Heads
        self.multi_task_head = MultiTaskHead(
            input_dim=hidden_dim,
            hidden_dim=hidden_dim // 2,
            dropout=head_dropout,
        )

    def forward(
        self,
        time_varying: Dict[str, torch.Tensor],
        static: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """Forward pass through the full model.

        Args:
            time_varying: Dict mapping layer names to tensors of shape
                (batch, seq_len, layer_dim).
            static: Static covariates of shape (batch, static_dim).

        Returns:
            Dictionary with keys:
                - 'disease_risks': (batch, num_horizons, num_diseases)
                - 'immune_risk_score': (batch, 1)
                - 'attention_weights': (batch, num_heads, seq_len, seq_len)
                - 'vsn_weights': dict of per-layer variable selection weights
        """
        batch_size = static.shape[0]
        seq_len = next(iter(time_varying.values())).shape[1]

        # 1. Encode static covariates -> context vectors
        static_contexts = self.static_encoder(static)
        vsn_context = static_contexts[0]  # Use first context for all VSNs

        # 2. Variable Selection per layer
        selected_features = []
        vsn_weights = {}
        for layer_name in self.layer_dims:
            x_layer = time_varying[layer_name]
            selected, weights = self.vsn_modules[layer_name](x_layer, vsn_context)
            selected_features.append(selected)
            vsn_weights[layer_name] = weights

        # 3. Concatenate selected features from all layers
        # (B, T, hidden_dim * num_layers)
        concat_features = torch.cat(selected_features, dim=-1)

        # 4. Temporal encoding (LSTM + GRN)
        encoded = self.temporal_encoder(concat_features)  # (B, T, hidden_dim)

        # 5. Ontology-informed attention
        attention_bias = self.ontology_prior.get_attention_bias(seq_len)
        attended, attention_weights = self.attention(encoded, attention_bias)

        # 6. Aggregate temporal representation (use last time step)
        aggregated = attended[:, -1, :]  # (B, hidden_dim)

        # 7. Multi-task disease prediction
        disease_risks, immune_risk = self.multi_task_head(aggregated)

        return {
            "disease_risks": disease_risks,
            "immune_risk_score": immune_risk,
            "attention_weights": attention_weights,
            "vsn_weights": vsn_weights,
        }


# ---------------------------------------------------------------------------
# Loss Function
# ---------------------------------------------------------------------------

class ImmuneTrajectoryLoss(nn.Module):
    """Combined loss for immune trajectory prediction.

    L_total = L_disease + lambda_1 * L_trajectory + lambda_2 * L_ontology

    - L_disease: Weighted BCE for multi-task disease prediction
    - L_trajectory: Allergic march trajectory consistency
    - L_ontology: KL divergence between attention and ontology prior
    """

    def __init__(
        self,
        disease_weights: Optional[List[float]] = None,
        lambda_trajectory: float = 0.1,
        lambda_ontology: float = 0.05,
    ) -> None:
        super().__init__()
        if disease_weights is None:
            # Inverse prevalence weighting
            disease_weights = [1.0, 1.2, 1.1, 2.0, 1.5, 3.0, 2.5]
        self.register_buffer(
            "disease_weights",
            torch.tensor(disease_weights, dtype=torch.float32),
        )
        self.lambda_trajectory = lambda_trajectory
        self.lambda_ontology = lambda_ontology

    def forward(
        self,
        predictions: Dict[str, torch.Tensor],
        targets: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """Compute combined loss.

        Args:
            predictions: Model output dictionary.
            targets: Target disease labels (batch, num_horizons, num_diseases).

        Returns:
            Dictionary with 'total', 'disease', 'trajectory', 'ontology' losses.
        """
        disease_risks = predictions["disease_risks"]

        # 1. Weighted BCE loss
        bce = F.binary_cross_entropy(disease_risks, targets, reduction="none")
        # Apply disease-specific weights: (1, 1, num_diseases)
        weighted_bce = bce * self.disease_weights.view(1, 1, -1)
        loss_disease = weighted_bce.mean()

        # 2. Trajectory consistency: AD(0) -> Asthma(1) -> Rhinitis(2)
        # Penalize if downstream risk exceeds upstream risk prematurely
        # Use 3-month horizon (index 3) for trajectory consistency
        risk_3m = disease_risks[:, 3, :]  # (B, 7)
        ad_risk = risk_3m[:, 0]
        asthma_risk = risk_3m[:, 1]
        rhinitis_risk = risk_3m[:, 2]

        # Soft constraint: asthma should not exceed AD, rhinitis should not exceed asthma
        loss_trajectory = (
            F.relu(asthma_risk - ad_risk).mean()
            + F.relu(rhinitis_risk - asthma_risk).mean()
        )

        # 3. Ontology alignment: attention weight regularization
        attn = predictions["attention_weights"]  # (B, H, T, T)
        # Encourage sparsity (proxy for ontology alignment)
        entropy = -(attn * (attn + 1e-8).log()).sum(dim=-1).mean()
        loss_ontology = entropy

        # Total loss
        loss_total = (
            loss_disease
            + self.lambda_trajectory * loss_trajectory
            + self.lambda_ontology * loss_ontology
        )

        return {
            "total": loss_total,
            "disease": loss_disease,
            "trajectory": loss_trajectory,
            "ontology": loss_ontology,
        }


# ---------------------------------------------------------------------------
# Dummy Data Generator
# ---------------------------------------------------------------------------

def create_dummy_data(
    batch_size: int = 8,
    seq_len: int = 90,
    layer_dims: Optional[Dict[str, int]] = None,
    static_dim: int = STATIC_DIM,
) -> Tuple[Dict[str, torch.Tensor], torch.Tensor, torch.Tensor]:
    """Create dummy data for testing the model architecture.

    Generates random tensors mimicking 90-day lookback windows of
    4-layer immune care data.

    Args:
        batch_size: Number of samples in the batch.
        seq_len: Number of time steps (days).
        layer_dims: Feature dimensions per layer.
        static_dim: Dimension of static covariates.

    Returns:
        time_varying: Dict of layer tensors (batch, seq_len, layer_dim).
        static: Static covariates (batch, static_dim).
        targets: Disease risk targets (batch, num_horizons, num_diseases).
    """
    if layer_dims is None:
        layer_dims = LAYER_DIMS

    time_varying = {}
    for layer_name, dim in layer_dims.items():
        time_varying[layer_name] = torch.randn(batch_size, seq_len, dim)

    static = torch.randn(batch_size, static_dim)

    # Binary targets for each disease at each horizon
    targets = torch.randint(0, 2, (batch_size, NUM_HORIZONS, NUM_DISEASES)).float()

    return time_varying, static, targets


# ---------------------------------------------------------------------------
# Training Loop Sketch
# ---------------------------------------------------------------------------

def training_loop_sketch(
    model: ImmuneTrajectoryModel,
    num_steps: int = 3,
    batch_size: int = 8,
    seq_len: int = 90,
    lr: float = 1e-3,
) -> None:
    """Sketch of a training loop for architecture validation.

    This is NOT a full training procedure. It verifies that:
    1. Forward pass produces correct output shapes
    2. Loss computation works
    3. Backward pass and gradient flow succeed

    Args:
        model: The ImmuneTrajectoryModel instance.
        num_steps: Number of training steps to run.
        batch_size: Batch size for dummy data.
        seq_len: Sequence length (lookback window).
        lr: Learning rate.
    """
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = ImmuneTrajectoryLoss()

    model.train()

    for step in range(num_steps):
        # Generate dummy data
        time_varying, static, targets = create_dummy_data(batch_size, seq_len)

        # Forward pass
        predictions = model(time_varying, static)

        # Compute loss
        losses = criterion(predictions, targets)

        # Backward pass
        optimizer.zero_grad()
        losses["total"].backward()
        optimizer.step()

        print(
            f"  Step {step + 1}/{num_steps} | "
            f"Total: {losses['total'].item():.4f} | "
            f"Disease: {losses['disease'].item():.4f} | "
            f"Trajectory: {losses['trajectory'].item():.4f} | "
            f"Ontology: {losses['ontology'].item():.4f}"
        )


# ---------------------------------------------------------------------------
# Main: Architecture Validation
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("Immune Trajectory Prediction Model - Architecture Validation")
    print("=" * 70)

    # 1. Create model
    print("\n[1] Creating ImmuneTrajectoryModel...")
    model = ImmuneTrajectoryModel(
        layer_dims=LAYER_DIMS,
        static_dim=STATIC_DIM,
        hidden_dim=128,
        attention_heads=4,
        lstm_layers=2,
        dropout=0.1,
        head_dropout=0.3,
        ontology_tau=1.0,
    )

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"    Total parameters:     {total_params:,}")
    print(f"    Trainable parameters: {trainable_params:,}")

    # 2. Create dummy data
    print("\n[2] Creating dummy data (batch=8, seq_len=90)...")
    time_varying, static, targets = create_dummy_data(batch_size=8, seq_len=90)
    print(f"    Static covariates:    {static.shape}")
    for name, tensor in time_varying.items():
        print(f"    {name:20s}: {tensor.shape}")
    print(f"    Targets:              {targets.shape}")

    # 3. Forward pass
    print("\n[3] Running forward pass...")
    model.eval()
    with torch.no_grad():
        outputs = model(time_varying, static)

    print(f"    disease_risks shape:     {outputs['disease_risks'].shape}")
    print(f"    immune_risk_score shape: {outputs['immune_risk_score'].shape}")
    print(f"    attention_weights shape: {outputs['attention_weights'].shape}")
    print(f"    VSN weight layers:       {list(outputs['vsn_weights'].keys())}")
    for name, w in outputs["vsn_weights"].items():
        print(f"      {name:20s}: {w.shape}")

    # 4. Verify output ranges
    print("\n[4] Verifying output ranges...")
    dr = outputs["disease_risks"]
    ir = outputs["immune_risk_score"]
    print(f"    disease_risks  min={dr.min().item():.4f}  max={dr.max().item():.4f}  (expected [0,1])")
    print(f"    immune_risk    min={ir.min().item():.2f}  max={ir.max().item():.2f}  (expected [0,100])")

    # 5. Print per-disease, per-horizon predictions for first sample
    print("\n[5] Sample predictions (patient 0):")
    print(f"    {'Disease':<25s} {'1day':>6s} {'1week':>6s} {'1month':>6s} {'3month':>6s}")
    print("    " + "-" * 51)
    for d_idx, d_name in enumerate(DISEASE_NAMES):
        risks = [f"{dr[0, h, d_idx].item():.3f}" for h in range(NUM_HORIZONS)]
        print(f"    {d_name:<25s} {risks[0]:>6s} {risks[1]:>6s} {risks[2]:>6s} {risks[3]:>6s}")
    print(f"    {'Immune Risk Score':<25s} {ir[0, 0].item():>6.1f}")

    # 6. Training loop sketch
    print("\n[6] Running training loop sketch (3 steps)...")
    model.train()
    training_loop_sketch(model, num_steps=3)

    # 7. Verify gradient flow
    print("\n[7] Verifying gradient flow...")
    grad_norms = {}
    for name, param in model.named_parameters():
        if param.grad is not None:
            grad_norms[name] = param.grad.norm().item()

    non_zero_grads = sum(1 for v in grad_norms.values() if v > 0)
    total_params_with_grad = len(grad_norms)
    print(f"    Parameters with gradients: {total_params_with_grad}")
    print(f"    Parameters with non-zero gradients: {non_zero_grads}")
    if non_zero_grads == total_params_with_grad:
        print("    [OK] All parameters received gradients.")
    else:
        zero_grad_params = [n for n, v in grad_norms.items() if v == 0]
        print(f"    [WARN] {len(zero_grad_params)} parameters have zero gradients:")
        for p in zero_grad_params[:5]:
            print(f"      - {p}")

    print("\n" + "=" * 70)
    print("Architecture validation complete.")
    print("=" * 70)

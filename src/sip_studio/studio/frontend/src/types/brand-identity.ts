/**
 * TypeScript types for Brand Identity - matching Python models exactly (snake_case).
 *
 * These types correspond to the Pydantic models in:
 * - src/sip_videogen/brands/models.py
 *
 * Field names use snake_case to match Python exactly (no mapping layer needed).
 */

// =============================================================================
// Supporting Types for Visual Identity
// =============================================================================

/**
 * Single color in the brand palette.
 * Maps to: ColorDefinition in models.py
 */
export interface ColorDefinition {
  hex: string
  name: string
  usage: string
}

/**
 * Typography specification for a specific use case.
 * Maps to: TypographyRule in models.py
 */
export interface TypographyRule {
  role: string
  family: string
  weight: string
  style_notes: string
}

// =============================================================================
// Identity Section Types
// =============================================================================

/**
 * Core brand identity - name, mission, story, values.
 * Maps to: BrandCoreIdentity in models.py
 */
export interface BrandCoreIdentity {
  name: string
  tagline: string
  mission: string
  brand_story: string
  values: string[]
}

/**
 * Complete visual design system for the brand.
 * Maps to: VisualIdentity in models.py
 */
export interface VisualIdentity {
  // Colors
  primary_colors: ColorDefinition[]
  secondary_colors: ColorDefinition[]
  accent_colors: ColorDefinition[]

  // Typography
  typography: TypographyRule[]

  // Imagery
  imagery_style: string
  imagery_keywords: string[]
  imagery_avoid: string[]

  // Materials & Textures
  materials: string[]

  // Logo
  logo_description: string
  logo_usage_rules: string

  // Overall
  overall_aesthetic: string
  style_keywords: string[]
}

/**
 * Brand voice and messaging guidelines.
 * Maps to: VoiceGuidelines in models.py
 */
export interface VoiceGuidelines {
  personality: string
  tone_attributes: string[]

  // Messaging
  key_messages: string[]
  messaging_do: string[]
  messaging_dont: string[]

  // Examples
  example_headlines: string[]
  example_taglines: string[]
}

/**
 * Target audience definition.
 * Maps to: AudienceProfile in models.py
 */
export interface AudienceProfile {
  primary_summary: string

  // Demographics
  age_range: string
  gender: string
  income_level: string
  location: string

  // Psychographics
  interests: string[]
  values: string[]
  lifestyle: string

  // Pain Points & Desires
  pain_points: string[]
  desires: string[]
}

/**
 * Market positioning and differentiation.
 * Maps to: CompetitivePositioning in models.py
 */
export interface CompetitivePositioning {
  market_category: string
  unique_value_proposition: string

  // Competitors
  primary_competitors: string[]
  differentiation: string

  // Positioning Statement
  positioning_statement: string
}

// =============================================================================
// Full Brand Identity (L1 Layer)
// =============================================================================

/**
 * Complete brand identity - the L1 layer.
 * Maps to: BrandIdentityFull in models.py
 */
export interface BrandIdentityFull {
  // Metadata
  slug: string
  created_at: string // ISO timestamp (serialized from Python datetime)
  updated_at: string // ISO timestamp (serialized from Python datetime)

  // Identity sections
  core: BrandCoreIdentity
  visual: VisualIdentity
  voice: VoiceGuidelines
  audience: AudienceProfile
  positioning: CompetitivePositioning

  // Constraints
  constraints: string[]
  avoid: string[]
}

// =============================================================================
// Section Types for Editing
// =============================================================================

/**
 * Union type for identity section names.
 * Used by update_brand_identity_section bridge method.
 */
export type IdentitySection =
  | 'core'
  | 'visual'
  | 'voice'
  | 'audience'
  | 'positioning'
  | 'constraints_avoid'

/**
 * Data shape for the constraints_avoid section.
 * This section combines the top-level constraints and avoid lists.
 */
export interface ConstraintsAvoidData {
  constraints: string[]
  avoid: string[]
}

/**
 * Type mapping for section names to their data types.
 */
export type SectionDataMap = {
  core: BrandCoreIdentity
  visual: VisualIdentity
  voice: VoiceGuidelines
  audience: AudienceProfile
  positioning: CompetitivePositioning
  constraints_avoid: ConstraintsAvoidData
}

// =============================================================================
// Backup Types
// =============================================================================

/**
 * Entry for a brand identity backup file.
 * Returned by list_identity_backups bridge method.
 */
export interface BackupEntry {
  filename: string
  timestamp: string // ISO timestamp
  size_bytes: number
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

type RequestOptions = RequestInit & {
  json?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    body: options.json ? JSON.stringify(options.json) : options.body,
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed");
  }

  return response.json() as Promise<T>;
}

export type ParticipantEditablePersonality = {
  extroversion: number;
  initiative: number;
  emotional_openness: number;
  attachment_style: string;
  conflict_style: string;
  self_esteem_stability: number;
  pace_preference: string;
  commitment_goal: string;
  preferred_traits: string[];
  disliked_traits: string[];
  boundaries: {
    hard_boundaries: string[];
    soft_boundaries: string[];
  };
  expression_style: {
    communication_style: string;
    reassurance_need: string;
  };
};

export type ParticipantImportPayload = {
  name: string;
  cast_role: string;
  age?: number;
  city?: string;
  occupation?: string;
  background_summary?: string;
  personality_summary?: string;
  attachment_style?: string;
  appearance_tags?: string[];
  personality_tags?: string[];
  preferred_traits?: string[];
  disliked_traits?: string[];
  commitment_goal?: string;
  editable_personality?: ParticipantEditablePersonality;
  is_active?: boolean;
  display_order?: number;
};

export type ParticipantImportRequest = {
  participants: ParticipantImportPayload[];
};

export type ProjectResponse = {
  id: string;
  name: string;
  description?: string;
  participant_count: number;
  created_at: string;
};

export type ProjectParticipant = {
  id: string;
  name: string;
  cast_role: string;
  city?: string;
  occupation?: string;
  attachment_style?: string;
  display_order: number;
  editable_personality: ParticipantEditablePersonality;
};

export type PersonalityPreset = {
  slug: string;
  name: string;
  description?: string;
  values: Partial<ParticipantEditablePersonality>;
};

export type ProjectParticipantsResponse = {
  project_id: string;
  project_name: string;
  participants: ProjectParticipant[];
  presets: PersonalityPreset[];
};

export type ParticipantCard = {
  participant_id: string;
  name: string;
  cast_role: string;
  display_order: number;
  personality_summary?: string;
  editable_personality: ParticipantEditablePersonality;
};

export type SceneTimelinePreview = {
  scene_run_id: string;
  scene_code: string;
  scene_index: number;
  status: string;
  summary?: string;
  tension?: string;
  replay_url?: string;
};

export type RelationshipCard = {
  source_participant_id: string;
  source_name: string;
  target_participant_id: string;
  target_name: string;
  relationship_kind: string;
  status: string;
  trend: string;
  top_reasons: string[];
  surface_metrics: Record<string, number>;
  last_event_tags: string[];
};

export type SimulationOverview = {
  id: string;
  project_id: string;
  status: string;
  current_scene_index: number;
  current_scene_code?: string;
  latest_scene_summary?: string;
  latest_audit_snippet?: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  error_message?: string;
  strategy_cards: string[];
  active_tension?: string;
  latest_scene_replay_url?: string;
  scene_timeline_preview: SceneTimelinePreview[];
  participants: ParticipantCard[];
  relationship_cards: RelationshipCard[];
  group_tension_summary?: string;
  hot_pairs: Array<{
    participant_a_id: string;
    participant_a_name: string;
    participant_b_id: string;
    participant_b_name: string;
    combined_score: number;
    summary: string;
  }>;
  isolated_participants: ParticipantCard[];
  relationship_graph_preview?: {
    node_count: number;
    edge_count: number;
    strongest_signals: RelationshipCard[];
  };
  recent_audit_logs: Array<{ log_type: string; payload: unknown; created_at: string }>;
};

export type SceneReplay = {
  simulation_id: string;
  scene_run_id: string;
  scene_code: string;
  scene_index: number;
  status: string;
  summary?: string;
  scene_plan?: {
    scene_id: string;
    scene_level?: string | null;
    scene_goal: string;
    scene_frame: string;
    participants: Array<{ participant_id: string; name: string; cast_role: string }>;
    min_turns: number;
    max_turns: number;
    planned_rounds: number;
    active_tension: string;
    stop_condition: string;
    scheduler_notes: string[];
    phase_outline: string[];
    participant_directives: Array<{ participant_id: string; directive: string }>;
  };
  messages: Array<{
    speaker_participant_id: string;
    speaker_name: string;
    turn_index: number;
    round_index: number;
    utterance: string;
    behavior_summary: string;
    intent_tags: string[];
    target_participant_ids: string[];
    addressed_from_turn_id?: string | null;
    topic_tags: string[];
    next_speaker_suggestions: string[];
    self_observation?: string | null;
  }>;
  rounds: Array<{
    round_index: number;
    phase_label?: string | null;
    turns: Array<{
      speaker_participant_id: string;
      speaker_name: string;
      turn_index: number;
      round_index: number;
      utterance: string;
      behavior_summary: string;
      intent_tags: string[];
      target_participant_ids: string[];
      addressed_from_turn_id?: string | null;
      topic_tags: string[];
      next_speaker_suggestions: string[];
      self_observation?: string | null;
    }>;
  }>;
  speaker_switch_summary: Array<{
    participant_id: string;
    name: string;
    turn_count: number;
    addressed_count: number;
  }>;
  major_events: Array<{
    title: string;
    description?: string | null;
    event_tags: string[];
    source_participant_id?: string | null;
    target_participant_ids: string[];
    linked_turn_indices: number[];
  }>;
  relationship_deltas: Array<{
    source_participant_id: string;
    target_participant_id: string;
    changes: Record<string, number>;
    reason: string;
    event_tags: string[];
  }>;
  pair_date_results: Array<{
    pair_index: number;
    participant_ids: string[];
    participant_names: string[];
    interaction_type: string;
    spark_level: string;
    summary: string;
    key_events: string[];
    relationship_deltas: Array<{
      source_participant_id: string;
      target_participant_id: string;
      changes: Record<string, number>;
      reason: string;
      event_tags: string[];
    }>;
    affects_future_candidate: boolean;
    level_semantic: string;
  }>;
  group_state_after_scene: {
    dominant_topics: string[];
    attention_distribution: Array<{ participant_id: string; name: string; mentions: number }>;
    tension_pairs: Array<{ participant_ids: string[]; names: string[]; pressure: number }>;
    isolated_participants: string[];
    matching_plan?: {
      pairs: Array<{
        pair_index: number;
        participant_a_id: string;
        participant_b_id: string;
      }>;
      waiting_participant_id?: string | null;
    };
    scene_level?: string;
  };
  next_tension?: string;
  replay_url?: string;
};

export type SimulationTimeline = {
  simulation_id: string;
  scenes: SceneTimelinePreview[];
};

export type SimulationRelationships = {
  simulation_id: string;
  participants: ParticipantCard[];
  relationships: RelationshipCard[];
};

export type SimulationRelationshipGraph = {
  simulation_id: string;
  group_tension_summary?: string;
  nodes: Array<{
    participant_id: string;
    name: string;
    cast_role: string;
    outgoing_score: number;
    incoming_score: number;
    total_score: number;
  }>;
  edges: Array<{
    source_participant_id: string;
    source_name: string;
    target_participant_id: string;
    target_name: string;
    score: number;
    status: string;
    trend: string;
    strongest_metric?: string | null;
    last_event_tags: string[];
  }>;
  strongest_signals: RelationshipCard[];
  hot_pairs: SimulationOverview["hot_pairs"];
  isolated_participants: ParticipantCard[];
};

export type SimulationPersonalities = {
  simulation_id: string;
  personalities: Array<{
    participant_id: string;
    name: string;
    cast_role: string;
    editable_personality: ParticipantEditablePersonality;
    changed_fields: string[];
    preset_slug?: string | null;
  }>;
};

export async function createProject(payload: {
  name: string;
  description?: string;
}) {
  return request<ProjectResponse>("/projects", {
    method: "POST",
    json: payload,
  });
}

export async function importParticipants(projectId: string, payload: ParticipantImportRequest) {
  return request(`/projects/${projectId}/participants/import`, {
    method: "POST",
    json: payload,
  });
}

export async function getProjectParticipants(projectId: string) {
  return request<ProjectParticipantsResponse>(`/projects/${projectId}/participants`);
}

export async function updateParticipantPersonality(
  projectId: string,
  participantId: string,
  editablePersonality: ParticipantEditablePersonality,
) {
  return request<{
    participant_id: string;
    name: string;
    cast_role: string;
    editable_personality: ParticipantEditablePersonality;
    changed_fields: string[];
  }>(`/projects/${projectId}/participants/${participantId}/personality`, {
    method: "PATCH",
    json: { editable_personality: editablePersonality },
  });
}

export async function listPersonalityPresets(projectId: string) {
  return request<PersonalityPreset[]>(`/projects/${projectId}/personality-presets`);
}

export async function applyPersonalityPreset(
  projectId: string,
  presetSlug: string,
  participantIds: string[],
) {
  return request<ProjectParticipantsResponse>(`/projects/${projectId}/personality-presets/apply`, {
    method: "POST",
    json: {
      preset_slug: presetSlug,
      participant_ids: participantIds,
    },
  });
}

export async function createSimulation(
  projectId: string,
  options: {
    strategyCards: string[];
    selectedParticipantIds?: string[];
    participantPersonalityOverrides?: Record<string, ParticipantEditablePersonality>;
    scenePackConfig?: Record<string, unknown>;
  },
) {
  return request<{ id: string }>(`/projects/${projectId}/simulations`, {
    method: "POST",
    json: {
      strategy_cards: options.strategyCards,
      selected_participant_ids: options.selectedParticipantIds ?? [],
      participant_personality_overrides: options.participantPersonalityOverrides ?? {},
      scene_pack_config: options.scenePackConfig ?? null,
    },
  });
}

export async function getSimulationOverview(simulationId: string) {
  return request<SimulationOverview>(`/simulations/${simulationId}`);
}

export async function getSimulationTimeline(simulationId: string) {
  return request<SimulationTimeline>(`/simulations/${simulationId}/timeline`);
}

export async function getSimulationRelationships(simulationId: string) {
  return request<SimulationRelationships>(`/simulations/${simulationId}/relationships`);
}

export async function getSimulationRelationshipGraph(simulationId: string) {
  return request<SimulationRelationshipGraph>(`/simulations/${simulationId}/relationship-graph`);
}

export async function getSimulationPersonalities(simulationId: string) {
  return request<SimulationPersonalities>(`/simulations/${simulationId}/personalities`);
}

export async function getSceneReplay(simulationId: string, sceneRunId: string) {
  return request<SceneReplay>(`/simulations/${simulationId}/scenes/${sceneRunId}`);
}

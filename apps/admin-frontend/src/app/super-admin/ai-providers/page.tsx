"use client";

import React, { useEffect, useState } from "react";
import { superAdminService } from "@/services/super-admin-service";
import { AIProviderConfig, AIProviderTestResult } from "@/types/admin";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Cpu,
  Plus,
  RefreshCw,
  Zap,
  CheckCircle,
  Sliders,
  X,
  Radio,
  Clock,
  RotateCcw,
} from "lucide-react";

export default function AIProvidersPage() {
  const [providers, setProviders] = useState<AIProviderConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Connectivity test results map: configId -> result
  const [testResults, setTestResults] = useState<Record<string, AIProviderTestResult>>({});
  const [testingId, setTestingId] = useState<string | null>(null);

  // New provider modal state
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newForm, setNewForm] = useState({
    provider_name: "gemini",
    model_name: "gemini-1.5-flash",
    is_primary: false,
    timeout_seconds: 15,
    max_retries: 3,
    temperature: 0.2,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Edit config modal
  const [editingConfig, setEditingConfig] = useState<AIProviderConfig | null>(null);
  const [editTemperature, setEditTemperature] = useState(0.2);
  const [editTimeout, setEditTimeout] = useState(15);
  const [editRetries, setEditRetries] = useState(3);

  const fetchProviders = async () => {
    setIsLoading(true);
    try {
      const res = await superAdminService.getAIProviders();
      if (res.success && res.data) {
        setProviders(res.data);
      }
    } catch (err) {
      console.error("Failed to load AI providers:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, []);

  const handleTestConnection = async (configId: string) => {
    setTestingId(configId);
    try {
      const res = await superAdminService.testAIProvider(configId);
      if (res.success && res.data) {
        setTestResults((prev) => ({ ...prev, [configId]: res.data! }));
      }
    } catch (err) {
      console.error("Connectivity probe failed:", err);
    } finally {
      setTestingId(null);
    }
  };

  const handleSetPrimary = async (configId: string) => {
    try {
      await superAdminService.updateAIProvider(configId, { is_primary: true });
      fetchProviders();
    } catch (err) {
      console.error("Failed to set primary provider:", err);
    }
  };

  const handleToggleActive = async (config: AIProviderConfig) => {
    try {
      await superAdminService.updateAIProvider(config.id, { is_active: !config.is_active });
      fetchProviders();
    } catch (err) {
      console.error("Failed to toggle provider active:", err);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      const res = await superAdminService.createAIProvider(newForm);
      if (res.success) {
        setIsAddOpen(false);
        setNewForm({
          provider_name: "gemini",
          model_name: "gemini-1.5-flash",
          is_primary: false,
          timeout_seconds: 15,
          max_retries: 3,
          temperature: 0.2,
        });
        fetchProviders();
      } else {
        setFormError(res.error || "Failed to register AI provider.");
      }
    } catch (err: any) {
      setFormError(err.message || "An unexpected error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveHyperparameters = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingConfig) return;
    setIsSubmitting(true);

    try {
      await superAdminService.updateAIProvider(editingConfig.id, {
        temperature: editTemperature,
        timeout_seconds: editTimeout,
        max_retries: editRetries,
      });
      setEditingConfig(null);
      fetchProviders();
    } catch (err) {
      console.error("Failed to save hyperparameters:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <Cpu className="h-5 w-5 text-[#6366F1]" />
            AI Provider Orchestration & Model Settings
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Configure primary LLM engines, secondary fallback routes, response temperature, and live connectivity probes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchProviders}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh models"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsAddOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium transition shadow-md shadow-[#6366F1]/20"
          >
            <Plus className="h-4 w-4" />
            <span>Add AI Provider</span>
          </button>
        </div>
      </div>

      {/* Provider Cards */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-xs text-[#A1A1AA]">
          <div className="flex flex-col items-center gap-2">
            <div className="w-5 h-5 border-2 border-[#6366F1] border-t-transparent rounded-full animate-spin" />
            <span>Checking AI model providers...</span>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {providers.map((p) => {
            const probe = testResults[p.id];
            const isTesting = testingId === p.id;

            return (
              <div
                key={p.id}
                className={`p-6 rounded-2xl border transition flex flex-col justify-between ${
                  p.is_primary
                    ? "border-[#6366F1] bg-[#111114] shadow-lg shadow-[#6366F1]/5"
                    : "border-[#2A2A30] bg-[#111114] hover:border-[#3F3F46]"
                }`}
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`p-2 rounded-xl ${
                          p.is_primary
                            ? "bg-[#6366F1]/10 text-[#6366F1]"
                            : "bg-[#1F1F23] text-[#A1A1AA]"
                        }`}
                      >
                        <Cpu className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-[#F5F5F5] capitalize">
                          {p.provider_name}
                        </h3>
                        <span className="text-[11px] font-mono text-[#6366F1] block">
                          {p.model_name}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-1">
                      {p.is_primary ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#6366F1] text-white uppercase tracking-wider">
                          Primary
                        </span>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#1F1F23] text-[#71717A] border border-[#2A2A30]">
                          Fallback
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Hyperparameters readout */}
                  <div className="grid grid-cols-3 gap-2 py-3 my-3 border-y border-[#1F1F23] text-center text-xs">
                    <div className="p-2 rounded-lg bg-[#18181B]">
                      <span className="text-[10px] text-[#71717A] block">Temp</span>
                      <span className="font-mono font-bold text-[#F5F5F5]">{p.temperature}</span>
                    </div>
                    <div className="p-2 rounded-lg bg-[#18181B]">
                      <span className="text-[10px] text-[#71717A] block">Timeout</span>
                      <span className="font-mono font-bold text-[#F5F5F5]">{p.timeout_seconds}s</span>
                    </div>
                    <div className="p-2 rounded-lg bg-[#18181B]">
                      <span className="text-[10px] text-[#71717A] block">Retries</span>
                      <span className="font-mono font-bold text-[#F5F5F5]">{p.max_retries}x</span>
                    </div>
                  </div>

                  {/* Connectivity Probe result if probed */}
                  {probe && (
                    <div className="mb-3 p-2.5 rounded-lg bg-[#10B981]/10 border border-[#10B981]/20 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5 text-[#10B981]">
                        <CheckCircle className="h-3.5 w-3.5" />
                        <span className="font-medium">Latency Verified</span>
                      </div>
                      <span className="font-mono font-bold text-[#10B981]">
                        {probe.latency_ms} ms
                      </span>
                    </div>
                  )}
                </div>

                {/* Card footer actions */}
                <div className="pt-2 flex items-center justify-between gap-2 border-t border-[#1F1F23]">
                  <button
                    onClick={() => handleTestConnection(p.id)}
                    disabled={isTesting}
                    className="flex-1 py-1.5 px-3 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#D4D4D8] transition flex items-center justify-center gap-1.5"
                  >
                    <Zap className={`h-3 w-3 ${isTesting ? "animate-spin text-[#F59E0B]" : "text-[#6366F1]"}`} />
                    <span>{isTesting ? "Testing..." : "Test Ping"}</span>
                  </button>

                  <button
                    onClick={() => {
                      setEditingConfig(p);
                      setEditTemperature(p.temperature);
                      setEditTimeout(p.timeout_seconds);
                      setEditRetries(p.max_retries);
                    }}
                    className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
                    title="Tune Hyperparameters"
                  >
                    <Sliders className="h-4 w-4" />
                  </button>

                  {!p.is_primary && (
                    <button
                      onClick={() => handleSetPrimary(p.id)}
                      className="py-1.5 px-2.5 rounded-lg bg-[#6366F1]/10 hover:bg-[#6366F1]/20 text-[#6366F1] text-xs font-medium transition"
                      title="Promote to Primary LLM"
                    >
                      Set Primary
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Provider Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setIsAddOpen(false)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Register AI Provider Model
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Add a new model for question-answering, vector generation, or fallback synthesis.
            </p>

            {formError && (
              <div className="mb-4 p-3 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444]">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Provider Ecosystem *
                </label>
                <select
                  value={newForm.provider_name}
                  onChange={(e) => {
                    const prov = e.target.value;
                    let defaultModel = "gemini-1.5-flash";
                    if (prov === "openai") defaultModel = "gpt-4o-mini";
                    if (prov === "groq") defaultModel = "llama-3.1-70b-versatile";
                    if (prov === "anthropic") defaultModel = "claude-3-5-haiku";
                    setNewForm({ ...newForm, provider_name: prov, model_name: defaultModel });
                  }}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                >
                  <option value="gemini">Google Gemini (Recommended Grounding Engine)</option>
                  <option value="openai">OpenAI</option>
                  <option value="groq">Groq (Ultra-low latency)</option>
                  <option value="anthropic">Anthropic Claude</option>
                </select>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Model Identifier *
                </label>
                <input
                  type="text"
                  required
                  value={newForm.model_name}
                  onChange={(e) => setNewForm({ ...newForm, model_name: e.target.value })}
                  placeholder="gemini-1.5-flash"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Temperature
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={newForm.temperature}
                    onChange={(e) => setNewForm({ ...newForm, temperature: parseFloat(e.target.value) })}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Timeout (s)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="60"
                    value={newForm.timeout_seconds}
                    onChange={(e) => setNewForm({ ...newForm, timeout_seconds: parseInt(e.target.value) })}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Retries
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="5"
                    value={newForm.max_retries}
                    onChange={(e) => setNewForm({ ...newForm, max_retries: parseInt(e.target.value) })}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-[#6366F1] hover:bg-[#4F46E5] text-white rounded-lg transition font-medium"
                >
                  {isSubmitting ? "Registering..." : "Add Provider"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Hyperparameters Modal */}
      {editingConfig && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-sm bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setEditingConfig(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1">
              Tune Hyperparameters
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Model: <span className="font-mono text-[#6366F1]">{editingConfig.model_name}</span>
            </p>

            <form onSubmit={handleSaveHyperparameters} className="space-y-4 text-xs">
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-[#A1A1AA] font-medium">Temperature (Creativity vs Factuality)</label>
                  <span className="font-mono text-[#F5F5F5]">{editTemperature}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={editTemperature}
                  onChange={(e) => setEditTemperature(parseFloat(e.target.value))}
                  className="w-full accent-[#6366F1]"
                />
                <span className="text-[10px] text-[#71717A] block mt-0.5">
                  Lower values (0.1 - 0.3) provide zero-hallucination factual grounding.
                </span>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Timeout (Seconds)
                </label>
                <input
                  type="number"
                  min="5"
                  max="60"
                  value={editTimeout}
                  onChange={(e) => setEditTimeout(parseInt(e.target.value))}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Max Retries On Transient Failures
                </label>
                <input
                  type="number"
                  min="0"
                  max="5"
                  value={editRetries}
                  onChange={(e) => setEditRetries(parseInt(e.target.value))}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-3 border-t border-[#2A2A30]">
                <button
                  type="button"
                  onClick={() => setEditingConfig(null)}
                  className="px-4 py-2 text-[#A1A1AA] hover:text-[#F5F5F5] bg-[#1F1F23] rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-[#6366F1] hover:bg-[#4F46E5] text-white rounded-lg transition font-medium"
                >
                  {isSubmitting ? "Saving..." : "Save Hyperparameters"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}


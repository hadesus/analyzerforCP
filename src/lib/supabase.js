import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Protocol storage functions
export const protocolStorage = {
  // Save a new protocol analysis
  async saveProtocol(filename, documentSummary, analysisResults) {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('User not authenticated')

    const { data, error } = await supabase
      .from('protocols')
      .insert({
        filename,
        document_summary: documentSummary,
        analysis_results: analysisResults,
        user_id: user.id
      })
      .select()
      .single()

    if (error) throw error

    // Save individual drugs for easier querying
    if (analysisResults && analysisResults.length > 0) {
      const drugInserts = analysisResults.map(result => ({
        protocol_id: data.id,
        drug_name_source: result.source_data?.drug_name_source,
        inn_name: result.normalization?.inn_name,
        dosage_source: result.source_data?.dosage_source,
        grade_level: result.ai_analysis?.ud_ai_grade,
        summary_note: result.ai_analysis?.ai_summary_note
      }))

      const { error: drugsError } = await supabase
        .from('protocol_drugs')
        .insert(drugInserts)

      if (drugsError) console.error('Error saving drugs:', drugsError)
    }

    return data
  },

  // Get all protocols for current user
  async getUserProtocols() {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('User not authenticated')

    const { data, error } = await supabase
      .from('protocols')
      .select(`
        *,
        protocol_drugs(count)
      `)
      .eq('user_id', user.id)
      .order('upload_date', { ascending: false })

    if (error) throw error
    return data
  },

  // Get specific protocol with full analysis
  async getProtocol(protocolId) {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('User not authenticated')

    const { data, error } = await supabase
      .from('protocols')
      .select('*')
      .eq('id', protocolId)
      .eq('user_id', user.id)
      .single()

    if (error) throw error
    return data
  },

  // Delete a protocol
  async deleteProtocol(protocolId) {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('User not authenticated')

    const { error } = await supabase
      .from('protocols')
      .delete()
      .eq('id', protocolId)
      .eq('user_id', user.id)

    if (error) throw error
  },

  // Search protocols by drug name
  async searchProtocolsByDrug(searchTerm) {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('User not authenticated')

    const { data, error } = await supabase
      .from('protocol_drugs')
      .select(`
        *,
        protocols!inner(*)
      `)
      .eq('protocols.user_id', user.id)
      .or(`drug_name_source.ilike.%${searchTerm}%,inn_name.ilike.%${searchTerm}%`)

    if (error) throw error
    return data
  }
}

// Authentication functions
export const auth = {
  async signUp(email, password) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: window.location.origin
      }
    })
    return { data, error }
  },

  async signIn(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    })
    return { data, error }
  },

  async signOut() {
    const { error } = await supabase.auth.signOut()
    return { error }
  },

  async getUser() {
    const { data: { user } } = await supabase.auth.getUser()
    return user
  },

  onAuthStateChange(callback) {
    return supabase.auth.onAuthStateChange(callback)
  }
}
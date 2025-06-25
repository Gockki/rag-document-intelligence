import { supabase } from './lib/supabase'

const testConnection = async () => {
  console.log('Testing Supabase connection...')
  const { data, error } = await supabase.auth.getSession()
  
  if (error) {
    console.error('Supabase error:', error)
  } else {
    console.log('Supabase connected!', data)
  }
}

testConnection()
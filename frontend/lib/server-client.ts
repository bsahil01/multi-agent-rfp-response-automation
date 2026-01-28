import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

type SupabaseEnv = {
    supabaseUrl: string;
    supabaseAnonKey: string;
};

function getEnvVar(): SupabaseEnv {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    
    const missing = [] as string[];
    if (!supabaseUrl) {
        missing.push("NEXT_PUBLIC_SUPABASE_URL");
    }
    if (!supabaseAnonKey) {
        missing.push("NEXT_PUBLIC_SUPABASE_ANON_KEY");
    }

    if (missing.length > 0) {
        throw new Error(`Missing environment variables: ${missing.join(", ")}`);
    }
    return { supabaseUrl, supabaseAnonKey };
}

export async function createSupabaseServerClient() {
    const { supabaseUrl, supabaseAnonKey } = getEnvVar();
    const cookieStore = cookies();

    return createServerClient(supabaseUrl, supabaseAnonKey, { 
        cookies: {
            getAll() {
                return cookieStore.getAll();
            },
            setAll(cookiesToSet) {
                try {
                    cookiesToSet.forEach(({ name, value, options }) =>
                        cookieStore.set(name, value, options)
                    );
                } catch (error) {
                    console.error("Error setting cookies:", error);
                }
            }
        }
    });
}
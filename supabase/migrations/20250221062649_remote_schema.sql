

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE EXTENSION IF NOT EXISTS "pgsodium" WITH SCHEMA "pgsodium";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgjwt" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";





SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."market-snapshots" (
    "id" bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT "now"() NOT NULL,
    "market" "text",
    "supply" bigint,
    "borrow" bigint,
    "withdraw" bigint,
    "repay" bigint,
    "interval" bigint,
    "total_supply" bigint,
    "total_borrow" bigint
);


ALTER TABLE "public"."market-snapshots" OWNER TO "postgres";


ALTER TABLE "public"."market-snapshots" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."market-snapshots_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."memories" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "text" "text" DEFAULT ''::"text",
    "type" "text" DEFAULT ''::"text"
);


ALTER TABLE "public"."memories" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."onchain-events" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "data" "json",
    "event" "text",
    "market" "text",
    "amount" bigint
);


ALTER TABLE "public"."onchain-events" OWNER TO "postgres";


COMMENT ON COLUMN "public"."onchain-events"."market" IS 'market id';



COMMENT ON COLUMN "public"."onchain-events"."amount" IS 'amount in USDC';



ALTER TABLE "public"."onchain-events" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."onchian-events_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



ALTER TABLE "public"."memories" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."thoughts_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."user-messages" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "text" "text" DEFAULT ''::"text",
    "sender" "text" DEFAULT ''::"text",
    "tx" "text" DEFAULT ''::"text"
);


ALTER TABLE "public"."user-messages" OWNER TO "postgres";


ALTER TABLE "public"."user-messages" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."user-messages_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



ALTER TABLE ONLY "public"."market-snapshots"
    ADD CONSTRAINT "market-snapshots_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."onchain-events"
    ADD CONSTRAINT "onchian-events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."memories"
    ADD CONSTRAINT "thoughts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user-messages"
    ADD CONSTRAINT "user-messages_pkey" PRIMARY KEY ("id");



CREATE POLICY "Enable Insert for all users" ON "public"."market-snapshots" FOR INSERT TO "anon" WITH CHECK (true);



CREATE POLICY "Enable insert for all users" ON "public"."memories" FOR INSERT TO "anon" WITH CHECK (true);



CREATE POLICY "Enable insert for all users" ON "public"."onchain-events" FOR INSERT TO "anon" WITH CHECK (true);



CREATE POLICY "Enable insert for all users" ON "public"."user-messages" FOR INSERT TO "anon" WITH CHECK (true);



CREATE POLICY "Enable read access for all users" ON "public"."market-snapshots" FOR SELECT TO "anon" USING (true);



CREATE POLICY "Enable read access for all users" ON "public"."memories" FOR SELECT TO "anon" USING (true);



CREATE POLICY "Enable read access for all users" ON "public"."onchain-events" FOR SELECT TO "anon" USING (true);



CREATE POLICY "Enable read access for all users" ON "public"."user-messages" FOR SELECT TO "anon" USING (true);



ALTER TABLE "public"."market-snapshots" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."memories" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."onchain-events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user-messages" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



































































































































































































GRANT ALL ON TABLE "public"."market-snapshots" TO "anon";
GRANT ALL ON TABLE "public"."market-snapshots" TO "authenticated";
GRANT ALL ON TABLE "public"."market-snapshots" TO "service_role";



GRANT ALL ON SEQUENCE "public"."market-snapshots_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."market-snapshots_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."market-snapshots_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."memories" TO "anon";
GRANT ALL ON TABLE "public"."memories" TO "authenticated";
GRANT ALL ON TABLE "public"."memories" TO "service_role";



GRANT ALL ON TABLE "public"."onchain-events" TO "anon";
GRANT ALL ON TABLE "public"."onchain-events" TO "authenticated";
GRANT ALL ON TABLE "public"."onchain-events" TO "service_role";



GRANT ALL ON SEQUENCE "public"."onchian-events_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."onchian-events_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."onchian-events_id_seq" TO "service_role";



GRANT ALL ON SEQUENCE "public"."thoughts_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."thoughts_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."thoughts_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."user-messages" TO "anon";
GRANT ALL ON TABLE "public"."user-messages" TO "authenticated";
GRANT ALL ON TABLE "public"."user-messages" TO "service_role";



GRANT ALL ON SEQUENCE "public"."user-messages_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."user-messages_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."user-messages_id_seq" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "service_role";






























RESET ALL;

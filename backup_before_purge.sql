--
-- PostgreSQL database dump
--

\restrict a8t0LemNk4pUezhbRD8c56TbxaKZA7lM6waaLsYflDbDCYAB2ecrOrPDrxsfoIn

-- Dumped from database version 16.10
-- Dumped by pg_dump version 16.10

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

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: availability; Type: TYPE; Schema: public; Owner: gymapp
--

CREATE TYPE public.availability AS ENUM (
    'present',
    'absent',
    'unknown'
);


ALTER TYPE public.availability OWNER TO gymapp;

--
-- Name: candidate_status; Type: TYPE; Schema: public; Owner: gymapp
--

CREATE TYPE public.candidate_status AS ENUM (
    'new',
    'reviewing',
    'approved',
    'rejected'
);


ALTER TYPE public.candidate_status OWNER TO gymapp;

--
-- Name: sourcetype; Type: TYPE; Schema: public; Owner: gymapp
--

CREATE TYPE public.sourcetype AS ENUM (
    'official_site',
    'on_site_signage',
    'user_submission',
    'media',
    'sns',
    'other'
);


ALTER TYPE public.sourcetype OWNER TO gymapp;

--
-- Name: submissionstatus; Type: TYPE; Schema: public; Owner: gymapp
--

CREATE TYPE public.submissionstatus AS ENUM (
    'pending',
    'corroborated',
    'approved',
    'rejected'
);


ALTER TYPE public.submissionstatus OWNER TO gymapp;

--
-- Name: verificationstatus; Type: TYPE; Schema: public; Owner: gymapp
--

CREATE TYPE public.verificationstatus AS ENUM (
    'unverified',
    'user_verified',
    'owner_verified',
    'admin_verified'
);


ALTER TYPE public.verificationstatus OWNER TO gymapp;

--
-- Name: refresh_gym_freshness(bigint); Type: FUNCTION; Schema: public; Owner: gymapp
--

CREATE FUNCTION public.refresh_gym_freshness(p_gym_id bigint) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_equipment_max TIMESTAMPTZ;
        v_gym_ts        TIMESTAMPTZ;
        v_new_cached    TIMESTAMPTZ;
    BEGIN
        SELECT MAX(e.last_verified_at) INTO v_equipment_max
        FROM gym_equipments ge
        JOIN equipments e ON e.id = ge.equipment_id
        WHERE ge.gym_id = p_gym_id;

        SELECT g.last_verified_at INTO v_gym_ts
        FROM gyms g
        WHERE g.id = p_gym_id
        FOR UPDATE;

        v_new_cached := GREATEST(
            COALESCE(v_gym_ts,        '-infinity'::timestamptz),
            COALESCE(v_equipment_max, '-infinity'::timestamptz)
        );

        UPDATE gyms
        SET last_verified_at_cached = v_new_cached
        WHERE id = p_gym_id;
    END;
    $$;


ALTER FUNCTION public.refresh_gym_freshness(p_gym_id bigint) OWNER TO gymapp;

--
-- Name: trg_refresh_on_equipment_del(); Type: FUNCTION; Schema: public; Owner: gymapp
--

CREATE FUNCTION public.trg_refresh_on_equipment_del() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_eid BIGINT := COALESCE(NEW.id, OLD.id);
        v_gid BIGINT;
    BEGIN
        FOR v_gid IN
            SELECT ge.gym_id FROM gym_equipments ge WHERE ge.equipment_id = v_eid
        LOOP
            PERFORM REFRESH_GYM_FRESHNESS(v_gid);
        END LOOP;
        RETURN NULL;
    END;
    $$;


ALTER FUNCTION public.trg_refresh_on_equipment_del() OWNER TO gymapp;

--
-- Name: trg_refresh_on_equipment_insupd(); Type: FUNCTION; Schema: public; Owner: gymapp
--

CREATE FUNCTION public.trg_refresh_on_equipment_insupd() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_eid BIGINT := COALESCE(NEW.id, OLD.id);
        v_gid BIGINT;
    BEGIN
        FOR v_gid IN
            SELECT ge.gym_id FROM gym_equipments ge WHERE ge.equipment_id = v_eid
        LOOP
            PERFORM REFRESH_GYM_FRESHNESS(v_gid);
        END LOOP;
        RETURN NULL;
    END;
    $$;


ALTER FUNCTION public.trg_refresh_on_equipment_insupd() OWNER TO gymapp;

--
-- Name: trg_refresh_on_gym_ts(); Type: FUNCTION; Schema: public; Owner: gymapp
--

CREATE FUNCTION public.trg_refresh_on_gym_ts() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        IF (OLD.last_verified_at IS DISTINCT FROM NEW.last_verified_at) THEN
            PERFORM REFRESH_GYM_FRESHNESS(NEW.id);
        END IF;
        RETURN NULL;
    END;
    $$;


ALTER FUNCTION public.trg_refresh_on_gym_ts() OWNER TO gymapp;

--
-- Name: trg_refresh_on_link_del(); Type: FUNCTION; Schema: public; Owner: gymapp
--

CREATE FUNCTION public.trg_refresh_on_link_del() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        PERFORM REFRESH_GYM_FRESHNESS(OLD.gym_id);
        RETURN NULL;
    END;
    $$;


ALTER FUNCTION public.trg_refresh_on_link_del() OWNER TO gymapp;

--
-- Name: trg_refresh_on_link_ins(); Type: FUNCTION; Schema: public; Owner: gymapp
--

CREATE FUNCTION public.trg_refresh_on_link_ins() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        PERFORM REFRESH_GYM_FRESHNESS(NEW.gym_id);
        RETURN NULL;
    END;
    $$;


ALTER FUNCTION public.trg_refresh_on_link_ins() OWNER TO gymapp;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO gymapp;

--
-- Name: equipments; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.equipments (
    id integer NOT NULL,
    name character varying NOT NULL,
    slug character varying NOT NULL,
    category character varying NOT NULL,
    description character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_verified_at timestamp with time zone
);


ALTER TABLE public.equipments OWNER TO gymapp;

--
-- Name: equipments_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.equipments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.equipments_id_seq OWNER TO gymapp;

--
-- Name: equipments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.equipments_id_seq OWNED BY public.equipments.id;


--
-- Name: favorites; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.favorites (
    device_id character varying NOT NULL,
    gym_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.favorites OWNER TO gymapp;

--
-- Name: geocode_caches; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.geocode_caches (
    id bigint NOT NULL,
    address text NOT NULL,
    latitude double precision,
    longitude double precision,
    provider character varying(32) NOT NULL,
    raw jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.geocode_caches OWNER TO gymapp;

--
-- Name: geocode_caches_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.geocode_caches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.geocode_caches_id_seq OWNER TO gymapp;

--
-- Name: geocode_caches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.geocode_caches_id_seq OWNED BY public.geocode_caches.id;


--
-- Name: gym_candidates; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.gym_candidates (
    id bigint NOT NULL,
    source_page_id bigint NOT NULL,
    name_raw text NOT NULL,
    address_raw text,
    pref_slug character varying(64),
    city_slug character varying(64),
    latitude double precision,
    longitude double precision,
    parsed_json jsonb,
    status public.candidate_status DEFAULT 'new'::public.candidate_status NOT NULL,
    duplicate_of_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.gym_candidates OWNER TO gymapp;

--
-- Name: gym_candidates_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.gym_candidates_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gym_candidates_id_seq OWNER TO gymapp;

--
-- Name: gym_candidates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.gym_candidates_id_seq OWNED BY public.gym_candidates.id;


--
-- Name: gym_equipments; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.gym_equipments (
    id integer NOT NULL,
    gym_id integer NOT NULL,
    equipment_id integer NOT NULL,
    availability public.availability NOT NULL,
    count integer,
    max_weight_kg integer,
    notes character varying,
    verification_status public.verificationstatus NOT NULL,
    last_verified_at timestamp with time zone,
    source_id integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT ck_gym_eq_count_nonneg CHECK (((count IS NULL) OR (count >= 0))),
    CONSTRAINT ck_gym_eq_maxw_nonneg CHECK (((max_weight_kg IS NULL) OR (max_weight_kg >= 0)))
);


ALTER TABLE public.gym_equipments OWNER TO gymapp;

--
-- Name: gym_equipments_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.gym_equipments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gym_equipments_id_seq OWNER TO gymapp;

--
-- Name: gym_equipments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.gym_equipments_id_seq OWNED BY public.gym_equipments.id;


--
-- Name: gym_images; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.gym_images (
    id integer NOT NULL,
    gym_id integer NOT NULL,
    url character varying NOT NULL,
    source character varying,
    verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.gym_images OWNER TO gymapp;

--
-- Name: gym_images_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.gym_images_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gym_images_id_seq OWNER TO gymapp;

--
-- Name: gym_images_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.gym_images_id_seq OWNED BY public.gym_images.id;


--
-- Name: gym_slugs; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.gym_slugs (
    id bigint NOT NULL,
    gym_id bigint NOT NULL,
    slug text NOT NULL,
    is_current boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.gym_slugs OWNER TO gymapp;

--
-- Name: gym_slugs_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.gym_slugs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gym_slugs_id_seq OWNER TO gymapp;

--
-- Name: gym_slugs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.gym_slugs_id_seq OWNED BY public.gym_slugs.id;


--
-- Name: gyms; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.gyms (
    id integer NOT NULL,
    name character varying NOT NULL,
    chain_name character varying,
    slug character varying NOT NULL,
    address character varying,
    pref character varying,
    city character varying,
    official_url character varying,
    affiliate_url character varying,
    owner_verified boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_verified_at_cached timestamp with time zone,
    last_verified_at timestamp with time zone,
    latitude double precision,
    longitude double precision,
    canonical_id uuid NOT NULL
);


ALTER TABLE public.gyms OWNER TO gymapp;

--
-- Name: gyms_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.gyms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gyms_id_seq OWNER TO gymapp;

--
-- Name: gyms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.gyms_id_seq OWNED BY public.gyms.id;


--
-- Name: reports; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.reports (
    id integer NOT NULL,
    gym_id integer NOT NULL,
    type character varying NOT NULL,
    message text NOT NULL,
    email character varying,
    source_url character varying,
    status character varying DEFAULT 'open'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.reports OWNER TO gymapp;

--
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reports_id_seq OWNER TO gymapp;

--
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.reports_id_seq OWNED BY public.reports.id;


--
-- Name: scraped_pages; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.scraped_pages (
    id bigint NOT NULL,
    source_id integer NOT NULL,
    url text NOT NULL,
    fetched_at timestamp with time zone NOT NULL,
    http_status integer,
    content_hash character(64),
    raw_html text,
    response_meta jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.scraped_pages OWNER TO gymapp;

--
-- Name: scraped_pages_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.scraped_pages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.scraped_pages_id_seq OWNER TO gymapp;

--
-- Name: scraped_pages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.scraped_pages_id_seq OWNED BY public.scraped_pages.id;


--
-- Name: sources; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.sources (
    id integer NOT NULL,
    source_type public.sourcetype NOT NULL,
    title character varying,
    url character varying,
    captured_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.sources OWNER TO gymapp;

--
-- Name: sources_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sources_id_seq OWNER TO gymapp;

--
-- Name: sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.sources_id_seq OWNED BY public.sources.id;


--
-- Name: user_submissions; Type: TABLE; Schema: public; Owner: gymapp
--

CREATE TABLE public.user_submissions (
    id integer NOT NULL,
    gym_id integer NOT NULL,
    equipment_id integer,
    payload_json character varying,
    photo_url character varying,
    visited_at timestamp with time zone,
    status public.submissionstatus NOT NULL,
    created_by_user_id integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_submissions OWNER TO gymapp;

--
-- Name: user_submissions_id_seq; Type: SEQUENCE; Schema: public; Owner: gymapp
--

CREATE SEQUENCE public.user_submissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_submissions_id_seq OWNER TO gymapp;

--
-- Name: user_submissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: gymapp
--

ALTER SEQUENCE public.user_submissions_id_seq OWNED BY public.user_submissions.id;


--
-- Name: equipments id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.equipments ALTER COLUMN id SET DEFAULT nextval('public.equipments_id_seq'::regclass);


--
-- Name: geocode_caches id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.geocode_caches ALTER COLUMN id SET DEFAULT nextval('public.geocode_caches_id_seq'::regclass);


--
-- Name: gym_candidates id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_candidates ALTER COLUMN id SET DEFAULT nextval('public.gym_candidates_id_seq'::regclass);


--
-- Name: gym_equipments id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_equipments ALTER COLUMN id SET DEFAULT nextval('public.gym_equipments_id_seq'::regclass);


--
-- Name: gym_images id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_images ALTER COLUMN id SET DEFAULT nextval('public.gym_images_id_seq'::regclass);


--
-- Name: gym_slugs id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_slugs ALTER COLUMN id SET DEFAULT nextval('public.gym_slugs_id_seq'::regclass);


--
-- Name: gyms id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gyms ALTER COLUMN id SET DEFAULT nextval('public.gyms_id_seq'::regclass);


--
-- Name: reports id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.reports ALTER COLUMN id SET DEFAULT nextval('public.reports_id_seq'::regclass);


--
-- Name: scraped_pages id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.scraped_pages ALTER COLUMN id SET DEFAULT nextval('public.scraped_pages_id_seq'::regclass);


--
-- Name: sources id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.sources ALTER COLUMN id SET DEFAULT nextval('public.sources_id_seq'::regclass);


--
-- Name: user_submissions id; Type: DEFAULT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.user_submissions ALTER COLUMN id SET DEFAULT nextval('public.user_submissions_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.alembic_version (version_num) FROM stdin;
c7cf8e913d2a
\.


--
-- Data for Name: equipments; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.equipments (id, name, slug, category, description, created_at, updated_at, last_verified_at) FROM stdin;
\.


--
-- Data for Name: favorites; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.favorites (device_id, gym_id, created_at) FROM stdin;
\.


--
-- Data for Name: geocode_caches; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.geocode_caches (id, address, latitude, longitude, provider, raw, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: gym_candidates; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.gym_candidates (id, source_page_id, name_raw, address_raw, pref_slug, city_slug, latitude, longitude, parsed_json, status, duplicate_of_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: gym_equipments; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.gym_equipments (id, gym_id, equipment_id, availability, count, max_weight_kg, notes, verification_status, last_verified_at, source_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: gym_images; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.gym_images (id, gym_id, url, source, verified, created_at) FROM stdin;
\.


--
-- Data for Name: gym_slugs; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.gym_slugs (id, gym_id, slug, is_current, created_at) FROM stdin;
\.


--
-- Data for Name: gyms; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.gyms (id, name, chain_name, slug, address, pref, city, official_url, affiliate_url, owner_verified, created_at, updated_at, last_verified_at_cached, last_verified_at, latitude, longitude, canonical_id) FROM stdin;
\.


--
-- Data for Name: reports; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.reports (id, gym_id, type, message, email, source_url, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: scraped_pages; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.scraped_pages (id, source_id, url, fetched_at, http_status, content_hash, raw_html, response_meta, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sources; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.sources (id, source_type, title, url, captured_at, created_at) FROM stdin;
\.


--
-- Data for Name: user_submissions; Type: TABLE DATA; Schema: public; Owner: gymapp
--

COPY public.user_submissions (id, gym_id, equipment_id, payload_json, photo_url, visited_at, status, created_by_user_id, created_at, updated_at) FROM stdin;
\.


--
-- Name: equipments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.equipments_id_seq', 1, false);


--
-- Name: geocode_caches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.geocode_caches_id_seq', 1, false);


--
-- Name: gym_candidates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.gym_candidates_id_seq', 1, false);


--
-- Name: gym_equipments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.gym_equipments_id_seq', 1, false);


--
-- Name: gym_images_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.gym_images_id_seq', 1, false);


--
-- Name: gym_slugs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.gym_slugs_id_seq', 1, false);


--
-- Name: gyms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.gyms_id_seq', 1, false);


--
-- Name: reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.reports_id_seq', 1, false);


--
-- Name: scraped_pages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.scraped_pages_id_seq', 1, false);


--
-- Name: sources_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.sources_id_seq', 1, false);


--
-- Name: user_submissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: gymapp
--

SELECT pg_catalog.setval('public.user_submissions_id_seq', 1, false);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: equipments equipments_name_key; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.equipments
    ADD CONSTRAINT equipments_name_key UNIQUE (name);


--
-- Name: equipments equipments_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.equipments
    ADD CONSTRAINT equipments_pkey PRIMARY KEY (id);


--
-- Name: equipments equipments_slug_key; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.equipments
    ADD CONSTRAINT equipments_slug_key UNIQUE (slug);


--
-- Name: favorites favorites_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.favorites
    ADD CONSTRAINT favorites_pkey PRIMARY KEY (device_id, gym_id);


--
-- Name: geocode_caches geocode_caches_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.geocode_caches
    ADD CONSTRAINT geocode_caches_pkey PRIMARY KEY (id);


--
-- Name: gym_candidates gym_candidates_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_candidates
    ADD CONSTRAINT gym_candidates_pkey PRIMARY KEY (id);


--
-- Name: gym_equipments gym_equipments_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_equipments
    ADD CONSTRAINT gym_equipments_pkey PRIMARY KEY (id);


--
-- Name: gym_images gym_images_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_images
    ADD CONSTRAINT gym_images_pkey PRIMARY KEY (id);


--
-- Name: gym_slugs gym_slugs_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_slugs
    ADD CONSTRAINT gym_slugs_pkey PRIMARY KEY (id);


--
-- Name: gym_slugs gym_slugs_slug_key; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_slugs
    ADD CONSTRAINT gym_slugs_slug_key UNIQUE (slug);


--
-- Name: gyms gyms_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gyms
    ADD CONSTRAINT gyms_pkey PRIMARY KEY (id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: scraped_pages scraped_pages_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.scraped_pages
    ADD CONSTRAINT scraped_pages_pkey PRIMARY KEY (id);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: geocode_caches uq_geocode_caches_address; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.geocode_caches
    ADD CONSTRAINT uq_geocode_caches_address UNIQUE (address);


--
-- Name: gym_equipments uq_gym_equipment_pair; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_equipments
    ADD CONSTRAINT uq_gym_equipment_pair UNIQUE (gym_id, equipment_id);


--
-- Name: gyms uq_gyms_slug; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gyms
    ADD CONSTRAINT uq_gyms_slug UNIQUE (slug);


--
-- Name: scraped_pages uq_scraped_pages_source_url; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.scraped_pages
    ADD CONSTRAINT uq_scraped_pages_source_url UNIQUE (source_id, url);


--
-- Name: user_submissions user_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.user_submissions
    ADD CONSTRAINT user_submissions_pkey PRIMARY KEY (id);


--
-- Name: idx_gym_equipments_gym_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX idx_gym_equipments_gym_id ON public.gym_equipments USING btree (gym_id);


--
-- Name: idx_gyms_fresh_id_desc; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX idx_gyms_fresh_id_desc ON public.gyms USING btree (last_verified_at_cached DESC, id DESC);


--
-- Name: idx_gyms_pref_city; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX idx_gyms_pref_city ON public.gyms USING btree (pref, city);


--
-- Name: ix_equipments_name_trgm; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_equipments_name_trgm ON public.equipments USING gin (name public.gin_trgm_ops);


--
-- Name: ix_gym_candidates_parsed_json; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_candidates_parsed_json ON public.gym_candidates USING gin (parsed_json);


--
-- Name: ix_gym_candidates_pref_city; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_candidates_pref_city ON public.gym_candidates USING btree (pref_slug, city_slug);


--
-- Name: ix_gym_candidates_status; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_candidates_status ON public.gym_candidates USING btree (status);


--
-- Name: ix_gym_eq_eq; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_eq_eq ON public.gym_equipments USING btree (equipment_id);


--
-- Name: ix_gym_eq_gym; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_eq_gym ON public.gym_equipments USING btree (gym_id);


--
-- Name: ix_gym_eq_last_verified; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_eq_last_verified ON public.gym_equipments USING btree (last_verified_at);


--
-- Name: ix_gym_eq_present; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_eq_present ON public.gym_equipments USING btree (gym_id) WHERE (availability = 'present'::public.availability);


--
-- Name: ix_gym_equipments_equipment_id_gym_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_equipments_equipment_id_gym_id ON public.gym_equipments USING btree (equipment_id, gym_id);


--
-- Name: ix_gym_equipments_gym_equipment; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_equipments_gym_equipment ON public.gym_equipments USING btree (gym_id, equipment_id);


--
-- Name: ix_gym_equipments_gym_id_equipment_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_equipments_gym_id_equipment_id ON public.gym_equipments USING btree (gym_id, equipment_id);


--
-- Name: ix_gym_images_created_at; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_images_created_at ON public.gym_images USING btree (created_at);


--
-- Name: ix_gym_images_gym_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_images_gym_id ON public.gym_images USING btree (gym_id);


--
-- Name: ix_gym_slugs_gym_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gym_slugs_gym_id ON public.gym_slugs USING btree (gym_id);


--
-- Name: ix_gyms_city_trgm; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_city_trgm ON public.gyms USING gin (city public.gin_trgm_ops);


--
-- Name: ix_gyms_freshness_paging; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_freshness_paging ON public.gyms USING btree (last_verified_at_cached DESC, id) WHERE (last_verified_at_cached IS NOT NULL);


--
-- Name: ix_gyms_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_id ON public.gyms USING btree (id);


--
-- Name: ix_gyms_last_verified_at_cached_desc_notnull; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_last_verified_at_cached_desc_notnull ON public.gyms USING btree (last_verified_at_cached DESC) WHERE (last_verified_at_cached IS NOT NULL);


--
-- Name: ix_gyms_last_verified_id_partial; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_last_verified_id_partial ON public.gyms USING btree (last_verified_at_cached, id) WHERE (last_verified_at_cached IS NOT NULL);


--
-- Name: ix_gyms_latitude; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_latitude ON public.gyms USING btree (latitude);


--
-- Name: ix_gyms_longitude; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_longitude ON public.gyms USING btree (longitude);


--
-- Name: ix_gyms_lvac_desc_id_asc_notnull; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_lvac_desc_id_asc_notnull ON public.gyms USING btree (last_verified_at_cached DESC, id) WHERE (last_verified_at_cached IS NOT NULL);


--
-- Name: ix_gyms_name_trgm; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_name_trgm ON public.gyms USING gin (name public.gin_trgm_ops);


--
-- Name: ix_gyms_pref_city; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_pref_city ON public.gyms USING btree (pref, city);


--
-- Name: ix_gyms_pref_city_lvac_desc_id_asc; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_pref_city_lvac_desc_id_asc ON public.gyms USING btree (pref, city, last_verified_at_cached DESC, id);


--
-- Name: ix_gyms_pref_city_lvac_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_gyms_pref_city_lvac_id ON public.gyms USING btree (pref, city, last_verified_at_cached DESC NULLS LAST, id);


--
-- Name: ix_gyms_slug; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE UNIQUE INDEX ix_gyms_slug ON public.gyms USING btree (slug);


--
-- Name: ix_reports_created_at; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_reports_created_at ON public.reports USING btree (created_at);


--
-- Name: ix_reports_gym_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_reports_gym_id ON public.reports USING btree (gym_id);


--
-- Name: ix_reports_status; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_reports_status ON public.reports USING btree (status);


--
-- Name: ix_scraped_pages_content_hash; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_scraped_pages_content_hash ON public.scraped_pages USING btree (content_hash);


--
-- Name: ix_scraped_pages_fetched_at_desc; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_scraped_pages_fetched_at_desc ON public.scraped_pages USING btree (fetched_at DESC);


--
-- Name: ix_sources_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE INDEX ix_sources_id ON public.sources USING btree (id);


--
-- Name: uq_gyms_canonical_id; Type: INDEX; Schema: public; Owner: gymapp
--

CREATE UNIQUE INDEX uq_gyms_canonical_id ON public.gyms USING btree (canonical_id);


--
-- Name: equipments trg_refresh_gym_freshness_del; Type: TRIGGER; Schema: public; Owner: gymapp
--

CREATE TRIGGER trg_refresh_gym_freshness_del AFTER DELETE ON public.equipments FOR EACH ROW EXECUTE FUNCTION public.trg_refresh_on_equipment_del();


--
-- Name: equipments trg_refresh_gym_freshness_insupd; Type: TRIGGER; Schema: public; Owner: gymapp
--

CREATE TRIGGER trg_refresh_gym_freshness_insupd AFTER INSERT OR UPDATE ON public.equipments FOR EACH ROW EXECUTE FUNCTION public.trg_refresh_on_equipment_insupd();


--
-- Name: gyms trg_refresh_gym_freshness_on_gym; Type: TRIGGER; Schema: public; Owner: gymapp
--

CREATE TRIGGER trg_refresh_gym_freshness_on_gym AFTER UPDATE OF last_verified_at ON public.gyms FOR EACH ROW EXECUTE FUNCTION public.trg_refresh_on_gym_ts();


--
-- Name: gym_equipments trg_refresh_on_link_del; Type: TRIGGER; Schema: public; Owner: gymapp
--

CREATE TRIGGER trg_refresh_on_link_del AFTER DELETE ON public.gym_equipments FOR EACH ROW EXECUTE FUNCTION public.trg_refresh_on_link_del();


--
-- Name: gym_equipments trg_refresh_on_link_ins; Type: TRIGGER; Schema: public; Owner: gymapp
--

CREATE TRIGGER trg_refresh_on_link_ins AFTER INSERT ON public.gym_equipments FOR EACH ROW EXECUTE FUNCTION public.trg_refresh_on_link_ins();


--
-- Name: favorites favorites_gym_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.favorites
    ADD CONSTRAINT favorites_gym_id_fkey FOREIGN KEY (gym_id) REFERENCES public.gyms(id) ON DELETE CASCADE;


--
-- Name: gym_candidates gym_candidates_duplicate_of_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_candidates
    ADD CONSTRAINT gym_candidates_duplicate_of_id_fkey FOREIGN KEY (duplicate_of_id) REFERENCES public.gym_candidates(id) ON DELETE SET NULL;


--
-- Name: gym_candidates gym_candidates_source_page_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_candidates
    ADD CONSTRAINT gym_candidates_source_page_id_fkey FOREIGN KEY (source_page_id) REFERENCES public.scraped_pages(id) ON DELETE CASCADE;


--
-- Name: gym_equipments gym_equipments_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_equipments
    ADD CONSTRAINT gym_equipments_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipments(id) ON DELETE CASCADE;


--
-- Name: gym_equipments gym_equipments_gym_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_equipments
    ADD CONSTRAINT gym_equipments_gym_id_fkey FOREIGN KEY (gym_id) REFERENCES public.gyms(id) ON DELETE CASCADE;


--
-- Name: gym_equipments gym_equipments_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_equipments
    ADD CONSTRAINT gym_equipments_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE SET NULL;


--
-- Name: gym_images gym_images_gym_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_images
    ADD CONSTRAINT gym_images_gym_id_fkey FOREIGN KEY (gym_id) REFERENCES public.gyms(id) ON DELETE CASCADE;


--
-- Name: gym_slugs gym_slugs_gym_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.gym_slugs
    ADD CONSTRAINT gym_slugs_gym_id_fkey FOREIGN KEY (gym_id) REFERENCES public.gyms(id) ON DELETE CASCADE;


--
-- Name: reports reports_gym_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_gym_id_fkey FOREIGN KEY (gym_id) REFERENCES public.gyms(id) ON DELETE CASCADE;


--
-- Name: scraped_pages scraped_pages_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.scraped_pages
    ADD CONSTRAINT scraped_pages_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE RESTRICT;


--
-- Name: user_submissions user_submissions_equipment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.user_submissions
    ADD CONSTRAINT user_submissions_equipment_id_fkey FOREIGN KEY (equipment_id) REFERENCES public.equipments(id) ON DELETE SET NULL;


--
-- Name: user_submissions user_submissions_gym_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: gymapp
--

ALTER TABLE ONLY public.user_submissions
    ADD CONSTRAINT user_submissions_gym_id_fkey FOREIGN KEY (gym_id) REFERENCES public.gyms(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict a8t0LemNk4pUezhbRD8c56TbxaKZA7lM6waaLsYflDbDCYAB2ecrOrPDrxsfoIn


CREATE TABLE [dbo].[FactTaxiDaily] (
    [date_key]           INT        NULL,
    [zone_id]            INT        NULL,
    [trips]              BIGINT     NULL,
    [passengers_sum]     BIGINT     NULL,
    [distance_miles_sum] FLOAT (53) NULL,
    [duration_min_sum]   FLOAT (53) NULL,
    [fare_usd_sum]       FLOAT (53) NULL,
    [tip_usd_sum]        FLOAT (53) NULL,
    [tolls_usd_sum]      FLOAT (53) NULL,
    [total_usd_sum]      FLOAT (53) NULL
);


GO
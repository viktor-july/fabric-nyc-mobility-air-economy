CREATE TABLE [dbo].[FactTaxiDaypart] (
    [date_key]      INT          NOT NULL,
    [zone_id]       INT          NOT NULL,
    [daypart]       VARCHAR (20) NOT NULL,
    [trips]         BIGINT       NULL,
    [total_usd_sum] FLOAT (53)   NULL
);


GO
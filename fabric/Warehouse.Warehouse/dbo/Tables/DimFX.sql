CREATE TABLE [dbo].[DimFX] (
    [date_key]    INT        NOT NULL,
    [date]        DATE       NOT NULL,
    [usd_per_eur] FLOAT (53) NOT NULL,
    [eur_per_usd] FLOAT (53) NOT NULL,
    [is_filled]   BIT        NOT NULL
);


GO

ALTER TABLE [dbo].[DimFX]
    ADD CONSTRAINT [PK_DimFX] PRIMARY KEY NONCLUSTERED ([date_key] ASC) NOT ENFORCED;


GO